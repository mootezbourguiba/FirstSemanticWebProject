import random
from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import XSD

# 1. Load your existing Ontology
input_file = "eco-tourism.rdf" 
g = Graph()

try:
    g.parse(input_file)
    print(f"✅ Successfully loaded {input_file} with {len(g)} triples.")
except Exception as e:
    print(f"❌ Error loading file: {e}")
    print("Make sure 'eco-tourism.rdf' is in the folder!")
    exit()

# 2. Define Namespace (Must match your Protégé IRI)
ECO = Namespace("http://www.semanticweb.org/eco-tourism#")
g.bind("eco", ECO)

# 3. Data Lists
cities = ["Tunis", "Tabarka", "Tozeur", "Djerba", "Sousse", "AinDraham"]
hotel_names = ["GreenStay", "EcoLodge", "NatureInn", "BlueOasis", "DesertCamp", "ForestHut"]
# Detailed activity names for the new classes
hiking_spots = ["Atlas Mountains Hike", "Oasis Trek", "Forest Walk", "Canyon Trail"]
diving_spots = ["Coral Reef Dive", "Shipwreck Explore", "Deep Blue Adventure"]
workshops = ["Pottery Masterclass", "Traditional Weaving", "Cooking Couscous", "Ceramics Art"]

# ---------------------------------------------------------
# PART A: GENERATE ACCOMMODATIONS (Hotels, EcoLodges, Camping)
# ---------------------------------------------------------
print("🚀 Generating Accommodations...")

for i in range(1, 51):
    # Unique ID
    uri = URIRef(ECO + f"Service_Accommodation_{i}")
    city_name = random.choice(cities)
    city_uri = URIRef(ECO + city_name)
    
    # Attributes
    price = random.randint(50, 300)
    co2 = round(random.uniform(5.0, 80.0), 2)
    rating = random.randint(1, 5)
    
    # Select Name randomly
    base_name = random.choice(hotel_names)
    full_name = f"{base_name} {city_name} {i}"
    
    # --- LOGIC: Decide Class based on Name/CO2 ---
    if "Camp" in base_name:
        # It is a Camping site
        g.add((uri, RDF.type, ECO.Camping))
        price = random.randint(30, 80) # Camping is cheaper
    elif co2 < 25:
        # Low CO2 = EcoLodge
        g.add((uri, RDF.type, ECO.EcoLodge))
    else:
        # Standard Hotel
        g.add((uri, RDF.type, ECO.Hotel))
        
    # --- RELATIONS ---
    # Link to City
    g.add((city_uri, RDF.type, ECO.City)) # Ensure City exists
    g.add((uri, ECO.isLocatedIn, city_uri))
    
    # Add Data Properties
    g.add((uri, ECO.hasName, Literal(full_name, datatype=XSD.string)))
    g.add((uri, ECO.hasPricePerNight, Literal(price, datatype=XSD.float)))
    g.add((uri, ECO.carbonFootprint, Literal(co2, datatype=XSD.double)))
    g.add((uri, ECO.ecoRating, Literal(rating, datatype=XSD.integer)))

    # Link to a generic activity (Old functionality kept for compatibility)
    # We will pick a random activity to say this hotel "offers" it
    random_act = random.choice(hiking_spots + diving_spots)
    act_uri = URIRef(ECO + f"Activity_Ref_{random.randint(1,999)}")
    g.add((uri, ECO.offersActivity, act_uri))

# ---------------------------------------------------------
# PART B: GENERATE STANDALONE ACTIVITIES (Hiking, Diving, Workshop)
# This matches your NEW Ontology Diagram
# ---------------------------------------------------------
print("🚀 Generating Activities...")

for i in range(1, 31):
    # Decide Type
    act_type = random.choice(["Hiking", "Diving", "Workshop"])
    city_name = random.choice(cities)
    city_uri = URIRef(ECO + city_name)
    uri = URIRef(ECO + f"Service_Activity_{i}")
    
    # Attributes for Activity
    price = random.randint(20, 120) # Activities are cheaper than hotels
    co2 = round(random.uniform(0.0, 15.0), 2) # Very eco-friendly
    rating = random.randint(3, 5)
    
    # Assign Class and Name
    if act_type == "Hiking":
        g.add((uri, RDF.type, ECO.Hiking))
        name = f"{random.choice(hiking_spots)} in {city_name}"
    elif act_type == "Diving":
        g.add((uri, RDF.type, ECO.Diving))
        name = f"{random.choice(diving_spots)} in {city_name}"
    else:
        g.add((uri, RDF.type, ECO.Workshop))
        name = f"{random.choice(workshops)} in {city_name}"

    # --- RELATIONS ---
    g.add((uri, ECO.isLocatedIn, city_uri))
    g.add((uri, ECO.hasName, Literal(name, datatype=XSD.string)))
    g.add((uri, ECO.hasPricePerNight, Literal(price, datatype=XSD.float)))
    g.add((uri, ECO.carbonFootprint, Literal(co2, datatype=XSD.double)))
    g.add((uri, ECO.ecoRating, Literal(rating, datatype=XSD.integer)))

# 5. Save the Result
output_file = "final_graph.ttl"
g.serialize(destination=output_file, format="turtle")

print(f"🎉 Success! Generated {len(g)} triples.")
print(f"📂 Saved as '{output_file}'. You will upload THIS file to Fuseki.")