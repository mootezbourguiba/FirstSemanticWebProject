# NOTE TO THE USER:
# The front-end for this application is in the 'index.html' file.
# If you are not seeing the latest changes (like Add/Edit/Delete buttons),
# please clear your browser's cache or perform a "hard refresh":
# - Windows/Linux: Ctrl+Shift+R
# - Mac: Cmd+Shift+R

from flask import Flask, jsonify, request, send_from_directory
from SPARQLWrapper import SPARQLWrapper, JSON
from flask_cors import CORS
import re
import uuid
import os

app = Flask(__name__)
CORS(app) 

# ---------------------------------------------------------
# 0. PAGE SERVING
# ---------------------------------------------------------
@app.route('/')
def root():
    return send_from_directory('.', 'index.html')

@app.route('/admin')
def admin_page():
    return send_from_directory('.', 'admin.html')

@app.route('/edit')
@app.route('/edit/<path:name>')
def edit_page(name=None):
    return send_from_directory('.', 'edit.html')

# 🔗 CONNECT TO FUSEKI
FUSEKI_URL = "http://localhost:3030/eco_db/query"
FUSEKI_URL_UPDATE = "http://localhost:3030/eco_db/update"
sparql = SPARQLWrapper(FUSEKI_URL)

def run_sparql_update(query):
    sparql_update = SPARQLWrapper(FUSEKI_URL_UPDATE)
    sparql_update.setMethod('POST')
    sparql_update.setQuery(query)
    try:
        sparql_update.query()
        return True
    except Exception as e:
        print(f"❌ Error contacting Fuseki for update: {e}")
        return False

def run_sparql_query(query):
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        return results["results"]["bindings"]
    except Exception as e:
        print(f"❌ Error contacting Fuseki: {e}")
        return []

def format_results(raw_data):
    """
    Cleans up the raw SPARQL JSON into a nice Python list
    """
    clean_results = []
    for item in raw_data:
        clean_results.append({
            "name": item.get("name", {}).get("value", "Unknown"),
            "city": item.get("city", {}).get("value", "Unknown"),
            "type": item.get("type", {}).get("value", "Service"), # New field: Hotel, Hiking, etc.
            "price": float(item.get("price", {}).get("value", 0)),
            "rating": int(item.get("rating", {}).get("value", 0)),
            "co2": float(item.get("co2", {}).get("value", 0)),
            "activity_name": item.get("activity_name", {}).get("value", "")
        })
    return clean_results

# ---------------------------------------------------------
# 1. MAIN SEARCH ENDPOINT (UPDATED)
# ---------------------------------------------------------
@app.route('/hotels', methods=['GET'])
def get_hotels():
    city_filter = request.args.get('city')
    
    # UPDATED QUERY: Finds ALL types (Hotel, Camping, Hiking, Diving, Workshop)
    # We use a large UNION block to capture everything.
    query_body = """
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    SELECT ?name ?city ?price ?rating ?co2 ?type
    WHERE {
      # 1. Identify the Type of Service
      { ?s a eco:EcoLodge . BIND("EcoLodge" AS ?type) }
      UNION { ?s a eco:Hotel . BIND("Hotel" AS ?type) }
      UNION { ?s a eco:Camping . BIND("Camping" AS ?type) }
      UNION { ?s a eco:Hiking . BIND("Hiking" AS ?type) }
      UNION { ?s a eco:Diving . BIND("Diving" AS ?type) }
      UNION { ?s a eco:Workshop . BIND("Workshop" AS ?type) }

      # 2. Get Attributes
      ?s eco:hasName ?name ;
         eco:isLocatedIn ?cityNode ;
         eco:hasPricePerNight ?price ;
         eco:ecoRating ?rating ;
         eco:carbonFootprint ?co2 .
      
      # 3. Extract City Name
      BIND(STRAFTER(STR(?cityNode), "#") AS ?city)
    """

    if city_filter and city_filter != "all":
        query_body += f'FILTER (REGEX(?city, "{city_filter}", "i"))\n'
    
    query_body += "}" # Close WHERE clause
    
    raw_data = run_sparql_query(query_body)
    return jsonify(format_results(raw_data))

# ---------------------------------------------------------
# 2. SMART AI CHATBOT (UPDATED)
# ---------------------------------------------------------
@app.route('/chat', methods=['POST'])
def chat_bot():
    """
    🧠 The AI now understands "Hiking", "Diving", "Workshop", "Camping"
    """
    user_text = request.json.get('message', '').lower()
    
    # Base Query (Same as above)
    query = """
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    SELECT ?name ?city ?price ?rating ?co2 ?type
    WHERE {
      { ?s a eco:EcoLodge . BIND("EcoLodge" AS ?type) }
      UNION { ?s a eco:Hotel . BIND("Hotel" AS ?type) }
      UNION { ?s a eco:Camping . BIND("Camping" AS ?type) }
      UNION { ?s a eco:Hiking . BIND("Hiking" AS ?type) }
      UNION { ?s a eco:Diving . BIND("Diving" AS ?type) }
      UNION { ?s a eco:Workshop . BIND("Workshop" AS ?type) }

      ?s eco:hasName ?name ;
         eco:isLocatedIn ?cityNode ;
         eco:hasPricePerNight ?price ;
         eco:ecoRating ?rating ;
         eco:carbonFootprint ?co2 .
      BIND(STRAFTER(STR(?cityNode), "#") AS ?city)
    """
    
    # A. DETECT CITY
    known_cities = ["tunis", "sousse", "djerba", "tozeur", "tabarka", "aindraham"]
    found_city = None
    for city in known_cities:
        if city in user_text:
            found_city = city
            query += f'FILTER (REGEX(?city, "{city}", "i"))\n'
            break
    
    # B. DETECT ACTIVITY TYPE (The New Logic)
    activity_type = None
    if "hike" in user_text or "hiking" in user_text:
        query += 'FILTER (?type = "Hiking")\n'
        activity_type = "hiking"
    elif "dive" in user_text or "diving" in user_text:
        query += 'FILTER (?type = "Diving")\n'
        activity_type = "diving"
    elif "camp" in user_text or "camping" in user_text:
        query += 'FILTER (?type = "Camping")\n'
        activity_type = "camping"
    elif "workshop" in user_text or "learn" in user_text:
        query += 'FILTER (?type = "Workshop")\n'
        activity_type = "workshop"

    # C. DETECT PRICE / RATING
    if "cheap" in user_text or "budget" in user_text:
        query += "} ORDER BY ASC(?price)"
    elif "expensive" in user_text or "luxury" in user_text:
        query += "} ORDER BY DESC(?price)"
    elif "best" in user_text or "top" in user_text:
        query += "} ORDER BY DESC(?rating)"
    else:
        query += "}" 

    print("🤖 Generated SPARQL:", query) # Debugging

    raw_data = run_sparql_query(query)
    results = format_results(raw_data)
    
    # Construct Reply
    if not results:
        bot_reply = "I couldn't find any eco-services matching your criteria."
    else:
        count = len(results)
        bot_reply = f"I found {count} results"
        
        if activity_type:
             bot_reply += f" for {activity_type}"
        else:
             bot_reply += " (Hotels & Activities)"
             
        if found_city:
            bot_reply += f" in {found_city.capitalize()}"
            
        if "cheap" in user_text:
            bot_reply += " starting with the cheapest."
        
    return jsonify({"response": bot_reply, "data": results})

# ---------------------------------------------------------
# 3. CRUD ENDPOINTS FOR ACCOMMODATION
# ---------------------------------------------------------
@app.route('/accommodation', methods=['POST'])
def add_accommodation():
    """Adds a new accommodation."""
    data = request.get_json()
    if not data or not all(k in data for k in ['name', 'city', 'type', 'price', 'rating', 'co2']):
        return jsonify({"error": "Missing data"}), 400

    new_id = str(uuid.uuid4())
    
    # The name of the new accommodation instance, using a UUID to ensure uniqueness
    accommodation_instance = f"eco:{data['name'].replace(' ', '_')}_{new_id[:8]}"
    city_instance = f"eco:{data['city'].capitalize()}"

    query = f"""
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    INSERT DATA {{
      {accommodation_instance} a eco:{data['type']} ;
                               eco:hasName "{data['name']}" ;
                               eco:isLocatedIn {city_instance} ;
                               eco:hasPricePerNight {data['price']} ;
                               eco:ecoRating {data['rating']} ;
                               eco:carbonFootprint {data['co2']} .
    }}
    """
    
    if run_sparql_update(query):
        return jsonify({"message": "Accommodation added successfully"}), 201
    else:
        return jsonify({"error": "Failed to add accommodation"}), 500

@app.route('/accommodation/<name>', methods=['DELETE'])
def delete_accommodation(name):
    """Deletes an accommodation by name."""
    
    query = f"""
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    DELETE WHERE {{
      ?s eco:hasName "{name}" ;
         ?p ?o .
    }}
    """
    
    if run_sparql_update(query):
        return jsonify({"message": f"Accommodation '{name}' deleted successfully"}), 200
    else:
        return jsonify({"error": "Failed to delete accommodation"}), 500

@app.route('/accommodation/<name>', methods=['PUT'])
def update_accommodation(name):
    """Updates an accommodation by name."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing data"}), 400

    # First, delete the old accommodation data
    delete_query = f"""
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    DELETE WHERE {{
      ?s eco:hasName "{name}" ;
         ?p ?o .
    }}
    """
    if not run_sparql_update(delete_query):
        return jsonify({"error": "Failed to delete old accommodation data for update"}), 500

    # Now, insert the new data
    new_id = str(uuid.uuid4())
    accommodation_instance = f"eco:{data.get('name', name).replace(' ', '_')}_{new_id[:8]}"
    city_instance = f"eco:{data['city'].capitalize()}"

    insert_query = f"""
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    INSERT DATA {{
      {accommodation_instance} a eco:{data.get('type')} ;
                               eco:hasName "{data.get('name', name)}" ;
                               eco:isLocatedIn {city_instance} ;
                               eco:hasPricePerNight {data.get('price')} ;
                               eco:ecoRating {data.get('rating')} ;
                               eco:carbonFootprint {data.get('co2')} .
    }}
    """

    if run_sparql_update(insert_query):
        return jsonify({"message": f"Accommodation '{name}' updated successfully"}), 200
    else:
        # Try to restore old data? For now, we just report the error.
        return jsonify({"error": "Failed to insert new accommodation data after update"}), 500


# ---------------------------------------------------------
# 4. HELPER ENDPOINTS
# ---------------------------------------------------------

@app.route('/cities', methods=['GET'])
def get_cities():
    """Returns a list of unique cities."""
    query = """
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    SELECT DISTINCT ?city
    WHERE {
      ?s eco:isLocatedIn ?cityNode .
      BIND(STRAFTER(STR(?cityNode), "#") AS ?city)
    }
    ORDER BY ?city
    """
    raw_data = run_sparql_query(query)
    cities_list = [item['city']['value'] for item in raw_data]
    return jsonify(cities_list)

@app.route('/recommendations', methods=['GET'])
def get_recommendations():
    """Returns top rated items across all categories"""
    query = """
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    SELECT ?name ?city ?price ?rating ?co2 ?type
    WHERE {
      { ?s a eco:EcoLodge . BIND("EcoLodge" AS ?type) }
      UNION { ?s a eco:Hotel . BIND("Hotel" AS ?type) }
      UNION { ?s a eco:Camping . BIND("Camping" AS ?type) }
      UNION { ?s a eco:Hiking . BIND("Hiking" AS ?type) }
      UNION { ?s a eco:Diving . BIND("Diving" AS ?type) }
      UNION { ?s a eco:Workshop . BIND("Workshop" AS ?type) }

      ?s eco:hasName ?name ;
         eco:isLocatedIn ?cityNode ;
         eco:hasPricePerNight ?price ;
         eco:ecoRating ?rating ;
         eco:carbonFootprint ?co2 .
      BIND(STRAFTER(STR(?cityNode), "#") AS ?city)
    }
    ORDER BY DESC(?rating)
    LIMIT 4
    """
    raw_data = run_sparql_query(query)
    return jsonify(format_results(raw_data))

@app.route('/hotel_details', methods=['GET'])
def get_hotel_details():
    """Returns all details for a specific hotel by name."""
    hotel_name = request.args.get('name')
    if not hotel_name:
        return jsonify({"error": "Hotel name is required"}), 400

    query = f"""
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    SELECT ?name ?city ?price ?rating ?co2 ?type ?activity_name
    WHERE {{
      ?s eco:hasName "{hotel_name}" ;
         eco:hasName ?name ;
         eco:isLocatedIn ?cityNode ;
         eco:hasPricePerNight ?price ;
         eco:ecoRating ?rating ;
         eco:carbonFootprint ?co2 .

      BIND(STRAFTER(STR(?cityNode), "#") AS ?city)

      # Determine the type of the service
      {{ ?s a eco:Hotel . BIND("Hotel" AS ?type) }}
      UNION {{ ?s a eco:Camping . BIND("Camping" AS ?type) }}
      UNION {{ ?s a eco:Hiking . BIND("Hiking" AS ?type) }}
      UNION {{ ?s a eco:Diving . BIND("Diving" AS ?type) }}
      UNION {{ ?s a eco:Workshop . BIND("Workshop" AS ?type) }}
      UNION {{ ?s a eco:EcoLodge . BIND("EcoLodge" AS ?type) }}

      # Optionally, find if this service offers an activity
      OPTIONAL {{
        ?activity eco:isOfferedBy ?s .
        ?activity eco:hasName ?activity_name .
      }}
    }}
    LIMIT 1
    """
    raw_data = run_sparql_query(query)
    
    # format_results returns a list, but we only expect one result
    results = format_results(raw_data)
    
    if results:
        return jsonify(results[0])
    else:
        return jsonify({"error": "Hotel not found"}), 404

if __name__ == '__main__':
    print("🚀 Starting Smart Eco-Backend on Port 5000...")
    app.run(debug=True, port=5000)