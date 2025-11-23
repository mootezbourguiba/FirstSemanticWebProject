import random
from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import XSD

# 1. Load your existing Ontology
# We use the file you just saved in Protégé
input_file = "eco-tourism.rdf" 
g = Graph()

try:
    g.parse(input_file)
    print(f"✅ Successfully loaded {input_file} with {len(g)} triples.")
except Exception as e:
    print(f"❌ Error loading file: {e}")
    print("Make sure the file name matches exactly!")
    exit()

# 2. Define Namespace (Must match your Protégé IRI)
# Check your Protégé 'Active Ontology' tab if this is different
ECO = Namespace("http://www.semanticweb.org/eco-tourism#")
g.bind("eco", ECO)

# 3. Mock Data Lists
cities = ["Tunis", "Tabarka", "Tozeur", "Djerba", "Sousse", "AinDraham"]
hotel_names = ["GreenStay", "EcoLodge", "NatureInn", "BlueOasis", "DesertCamp", "ForestHut"]
activities = ["Hiking", "Diving", "PotteryWorkshop", "CamelRide", "BirdWatching"]

# 4. Generate 50 Mock Services
print("🚀 Generating data...")

for i in range(1, 51):
    # Create a unique ID for this hotel
    hotel_uri = URIRef(ECO + f"Accommodation_{i}")
    city_name = random.choice(cities)
    city_uri = URIRef(ECO + city_name)
    
    # Random attributes
    price = random.randint(50, 300)
    co2 = round(random.uniform(5.0, 80.0), 2) # kg CO2 per night
    rating = random.randint(1, 5)
    name = f"{random.choice(hotel_names)} {city_name} {i}"
    
    # --- ADD TRIPLES ---
    
    # 1. Define Type: Randomly choose EcoLodge or Hotel
    if co2 < 20:
        g.add((hotel_uri, RDF.type, ECO.EcoLodge))
    else:
        g.add((hotel_uri, RDF.type, ECO.Hotel))
        
    # 2. Define Location (and ensure City exists)
    g.add((city_uri, RDF.type, ECO.City))
    g.add((hotel_uri, ECO.isLocatedIn, city_uri))
    
    # 3. Add Data Properties
    g.add((hotel_uri, ECO.hasName, Literal(name, datatype=XSD.string)))
    g.add((hotel_uri, ECO.hasPricePerNight, Literal(price, datatype=XSD.float)))
    g.add((hotel_uri, ECO.carbonFootprint, Literal(co2, datatype=XSD.double)))
    g.add((hotel_uri, ECO.ecoRating, Literal(rating, datatype=XSD.integer)))

    # 4. Link to an Activity (Offers Activity)
    act_name = random.choice(activities)
    act_uri = URIRef(ECO + f"Activity_{act_name}")
    g.add((act_uri, RDF.type, ECO.Activity))
    g.add((act_uri, ECO.hasName, Literal(act_name)))
    
    g.add((hotel_uri, ECO.offersActivity, act_uri))

# 5. Save the Result
output_file = "final_graph.ttl"
g.serialize(destination=output_file, format="turtle")

print(f"🎉 Success! Generated {len(g)} triples.")
print(f"📂 Saved as '{output_file}'. You will upload THIS file to Fuseki.")