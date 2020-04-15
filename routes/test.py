import pymongo
from bson.json_util import dumps 

USERNAME    = "food"
PASSWORD    = "CHANGETHISPASSWORD_ITSREAD_ONLY_THO"
HOST        = "localhost"
PORT        = "27017"

MONGO_DB_IP = f"mongodb://food:changeme@localhost:27017/"

my_client = pymongo.MongoClient(MONGO_DB_IP)
db = my_client["resources"]

print(db.collection_names())
collection = db["food_banks"]

item = collection.find({})

for i in item:
    print(i)
# print(item[0])