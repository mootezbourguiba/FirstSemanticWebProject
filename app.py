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
    # ... (This is the standard list endpoint, simplified for brevity) ...
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
    """
    raw_data = run_sparql_query(query)
    return format_results(raw_data)

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
            "name": item["name"]["value"],
            "city": item["city"]["value"],
            "price": float(item["price"]["value"]),
            "rating": int(item["rating"]["value"]),
            "co2": float(item["co2"]["value"])
        })
    return clean_results

if __name__ == '__main__':
    app.run(debug=True, port=5000)