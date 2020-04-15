# pandemics-api
API for pandemics.live that supports Inventory Querying, Data Management, and Resource Finding

# resources-API

The resource API uses mongoDB as the DBMS required. To setup mongodb use the setup_mongo.sh script. Please make sure to change both the admin and food user passwords before running the script.

```zsh
pip3 install pymongo
sudo ./setup_mongo.sh mongo.json
```
In the routes/resources.py file update the passwords to accommodate the changes made to the passwords in the setup_mongo.sh

Upon doing this and all the other normal pandemics-api dependencies are doneyou can run the api.py file. 

Example Queries:
/v1/resources/get_locations 
/v1/resources/food_banks?state=CT&town=West%20Haven

## Resources API Notice
The mongo.json file must be ran with the setup_mongo.sh the reason for this is it creates a database based on the json file. 
