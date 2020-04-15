from flask import Blueprint, request, jsonify, escape
import pymongo

USERNAME    = "food"
PASSWORD    = "changeme"
HOST        = "localhost"
PORT        = "27017"

MONGO_DB_IP = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/?authSource=admin"


# Blueprinting which allows multiple routes
resources_api = Blueprint("resources_api", __name__, template_folder="templates")

JSON_DATA = None # for caching

@resources_api.route("/v1/resources")
# TODO: give example how to query
def resources():
    return "hi"


@resources_api.route("/v1/resources/get_locations", methods=['GET'])
def get_locations():
    """Used to return the states and the towns for querying."""

    global JSON_DATA
    if JSON_DATA is None: # if not cached
        my_client = pymongo.MongoClient(MONGO_DB_IP)

        food_banks = my_client["resources"]["food_banks"] # get food_banks db
        locations = food_banks.find({}, 
            {
                "food_banks.town": 1,  # each 1 represent key to enable.
                "state": 1, 
                "full_name": 1,
                "_id":0
            }
        )

        JSON_DATA = [item for item in locations] # query list in arr.

        my_client.close()

    return jsonify(JSON_DATA)



@resources_api.route("/v1/resources/food_banks", methods=['GET'])
def get_food_banks():
<<<<<<< HEAD
    """This function is used to query MongoDB to return list of food banks"""
=======
    """This function is used to query MongoDB to return list of food banks
    
        example:
            /v1/resources/food_banks?state=CT&town=West%20Haven
    """
>>>>>>> resourcesAPi

    if len(request.args) != 2:
        return jsonify({"error": "Please use two arguments state & town"})
        
    my_client = pymongo.MongoClient(MONGO_DB_IP)

    food_banks = my_client["resources"]["food_banks"]

    locations = food_banks.find_one(
        {
            # escaping strings to prevent injection.
            "food_banks.town": escape(request.args.get("town")), 
            "state":  escape(request.args.get("state"))
        }, 
        {
            "food_banks.town.$": 1,
             "food_banks.location": 1,
            "_id": 0
        }
    )

    my_client.close() 
    json_data = locations

    if json_data is None:
        return jsonify({"error": "item not found"})

    return jsonify(json_data["food_banks"][0])