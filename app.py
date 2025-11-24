from flask import Flask, jsonify, request
from SPARQLWrapper import SPARQLWrapper, JSON
from flask_cors import CORS
import re # Regular Expressions for text analysis

app = Flask(__name__)
CORS(app) 

FUSEKI_URL = "http://localhost:3030/eco_db/query"
sparql = SPARQLWrapper(FUSEKI_URL)

def run_sparql_query(query):
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        return results["results"]["bindings"]
    except Exception as e:
        print(f"❌ Error contacting Fuseki: {e}")
        return []

@app.route('/hotels', methods=['GET'])
def get_hotels():
    city_filter = request.args.get('city')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')

    query_body = """
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    SELECT ?name ?city ?price ?rating ?co2
    WHERE {
      { ?hotel a eco:EcoLodge } UNION { ?hotel a eco:Hotel } .
      ?hotel eco:hasName ?name ;
             eco:isLocatedIn ?cityNode ;
             eco:hasPricePerNight ?price ;
             eco:ecoRating ?rating ;
             eco:carbonFootprint ?co2 .
      BIND(STRAFTER(STR(?cityNode), "#") AS ?city)
    """

    if city_filter and city_filter != "all":
        query_body += f'FILTER (REGEX(?city, "{city_filter}", "i"))\n'
    
    if min_price and max_price:
        try:
            # Add filter for the price range
            query_body += f'FILTER (?price >= {float(min_price)} && ?price <= {float(max_price)})\n'
        except ValueError:
            # Handle cases where price is not a valid float
            pass
    
    query_body += "}" # Close WHERE clause
    
    raw_data = run_sparql_query(query_body)
    return jsonify(format_results(raw_data))

@app.route('/chat', methods=['POST'])
def chat_bot():
    """
    🧠 The "Smart Logic" AI
    Converts natural language -> SPARQL Query
    """
    user_text = request.json.get('message', '').lower()
    
    # 1. Base Query
    query = """
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    SELECT ?name ?city ?price ?rating ?co2
    WHERE {
      { ?hotel a eco:EcoLodge } UNION { ?hotel a eco:Hotel } .
      ?hotel eco:hasName ?name ;
             eco:isLocatedIn ?cityNode ;
             eco:hasPricePerNight ?price ;
             eco:ecoRating ?rating ;
             eco:carbonFootprint ?co2 .
      BIND(STRAFTER(STR(?cityNode), "#") AS ?city)
    """
    
    # 2. 🌍 DETECT CITY (Keyword Extraction)
    # List of known cities in your DB
    known_cities = ["tunis", "sousse", "djerba", "tozeur", "tabarka"]
    found_city = None
    for city in known_cities:
        if city in user_text:
            found_city = city
            query += f'FILTER (REGEX(?city, "{city}", "i"))\n'
            break
    
    # 3. 💰 DETECT PRICE PREFERENCE
    if "cheap" in user_text or "budget" in user_text or "low cost" in user_text:
        # Sort by Price ASC
        query += "} ORDER BY ASC(?price)"
    elif "luxury" in user_text or "expensive" in user_text:
        # Sort by Price DESC
        query += "} ORDER BY DESC(?price)"
    elif "best" in user_text or "top" in user_text:
         # Sort by Rating DESC
        query += "} ORDER BY DESC(?rating)"
    else:
        query += "}" # Close the query normally

    print("🤖 Generated SPARQL:", query) # Debugging: See the query in terminal

    # 4. Run the constructed query
    raw_data = run_sparql_query(query)
    results = format_results(raw_data)
    
    # 5. Generate a "Bot Response" text
    if not results:
        bot_reply = "I couldn't find any eco-lodges matching your criteria. Try a different city!"
    else:
        count = len(results)
        bot_reply = f"I found {count} eco-friendly places for you"
        if found_city:
            bot_reply += f" in {found_city.capitalize()}"
        if "cheap" in user_text:
            bot_reply += " starting with the cheapest ones."
        
    return jsonify({"response": bot_reply, "data": results})

def format_results(raw_data):
    clean_results = []
    for item in raw_data:
        clean_results.append({
            "name": item.get("name", {}).get("value"),
            "city": item.get("city", {}).get("value"),
            "price": float(item.get("price", {}).get("value", 0)),
            "rating": int(item.get("rating", {}).get("value", 0)),
            "co2": float(item.get("co2", {}).get("value", 0)),
            "activity_name": item.get("activity_name", {}).get("value")
        })
    return clean_results

def format_single_result(raw_data):
    if not raw_data:
        return {}
    item = raw_data[0]
    return {
        "name": item.get("name", {}).get("value"),
        "city": item.get("city", {}).get("value"),
        "price": float(item.get("price", {}).get("value", 0)),
        "rating": int(item.get("rating", {}).get("value", 0)),
        "co2": float(item.get("co2", {}).get("value", 0)),
        "activity_name": item.get("activity_name", {}).get("value")
    }

@app.route('/hotel_details', methods=['GET'])
def get_hotel_details():
    hotel_name = request.args.get('name')
    if not hotel_name:
        return jsonify({"error": "Hotel name is required"}), 400

    query = f"""
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT ?name ?city ?price ?rating ?co2 ?activity_name
    WHERE {{
      ?hotel eco:hasName "{hotel_name}"^^xsd:string .
      ?hotel eco:hasName ?name ;
             eco:isLocatedIn ?cityNode ;
             eco:hasPricePerNight ?price ;
             eco:ecoRating ?rating ;
             eco:carbonFootprint ?co2 .
      OPTIONAL {{ 
          ?hotel eco:offersActivity ?activity .
          ?activity eco:hasName ?activity_name .
      }}
      BIND(STRAFTER(STR(?cityNode), "#") AS ?city)
    }}
    LIMIT 1
    """
    raw_data = run_sparql_query(query)
    return jsonify(format_single_result(raw_data))

@app.route('/price_range', methods=['GET'])
def get_price_range():
    """Returns the min and max price for all hotels."""
    query = """
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    SELECT (MIN(?price) as ?min_price) (MAX(?price) as ?max_price)
    WHERE {
      ?hotel eco:hasPricePerNight ?price .
    }
    """
    raw_data = run_sparql_query(query)
    if raw_data and raw_data[0]['min_price'] and raw_data[0]['max_price']:
        price_range = {
            "min_price": float(raw_data[0]['min_price']['value']),
            "max_price": float(raw_data[0]['max_price']['value'])
        }
        return jsonify(price_range)
    return jsonify({"min_price": 0, "max_price": 1000}) # Fallback

@app.route('/cities', methods=['GET'])
def get_cities():
    """Returns a list of unique cities."""
    query = """
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    SELECT DISTINCT ?city
    WHERE {
      ?hotel eco:isLocatedIn ?cityNode .
      BIND(STRAFTER(STR(?cityNode), "#") AS ?city)
    }
    ORDER BY ?city
    """
    raw_data = run_sparql_query(query)
    # Flatten the list of dictionaries into a simple list of strings
    cities_list = [item['city']['value'] for item in raw_data]
    return jsonify(cities_list)

@app.route('/recommendations', methods=['GET'])
def get_recommendations():
    """Returns the top 4 highest-rated hotels."""
    query = """
    PREFIX eco: <http://www.semanticweb.org/eco-tourism#>
    SELECT ?name ?city ?price ?rating ?co2
    WHERE {
      { ?hotel a eco:EcoLodge } UNION { ?hotel a eco:Hotel } .
      ?hotel eco:hasName ?name ;
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)