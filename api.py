import requests
from lxml import html
from bs4 import BeautifulSoup
import json
import time
import geopy
from geopy.geocoders import Nominatim
from flask import Flask
from flask import request
from flask import render_template
from flask import jsonify

# api future:
# /searchBy?method=upc&store=walmart&itemCode=044600301129&zipCode=06516

app = Flask(__name__)

# supported stores to query
upcStores = ["walmart", "target", "lowes", "office-depot", "macys", "staples"]
skuStores = ["cvs", "bjs"]

''' fetchBrickseed(): fetch inventory levels from brickSeed
        store: store name (for URL)
        itemID: upc or sku
        idType: upc or sku
        zipCode: user zipCode'''
def fetchBrickseed(store, itemID, idType, zipCode):
    data = {
    'zip': zipCode,
    'method': idType
    }

    # headers NEED user-agent to bypass cloudflare and host to bypass weak filter to prevent spam
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:10.0) Gecko/20100101 Firefox/10.0',
        'Host': 'brickseek.com'
    }

    # prepare request and send it to the server
    req = requests.Request('POST', 'https://brickseek.com/{}-inventory-checker/?{}={}'.format(store, idType, itemID), data=data, headers=headers)
    prepared = req.prepare()
    s = requests.Session()
    res = s.send(prepared)

    # parse response and extract table of results for parsing
    soup = BeautifulSoup(res.text, 'html.parser')
    return soup.find(class_="table__body")



''' parseHTML(): fetch inventory levels from brickSeed
        store: store name
        results: html table'''
def parseHTML(store, results):
    inventoryByStore = {}       # master list for storinng data
 
    if results is None:
        return None

    # parse out store information and stock information    
    tree = html.fromstring(str(results))
    stores = tree.xpath('//strong[@class="address-location-name"]/text()')
    address = tree.xpath('//address[@class="address"]/text()')
    stock = tree.xpath('//span[@class="availability-status-indicator__text"]/text()')
    dollars = tree.xpath('//span[@class="price-formatted__dollars"]/text()')
    cents = tree.xpath('//span[@class="price-formatted__cents"]/text()')

    inventLevels = {}
    ct = 0
    for entry in stores:
        try:   
            storeAddress = address[(ct * 4)].strip() + ", " + address[(ct * 4) + 1].strip()
        except:
            storeAddress = "Unknown"
        
        try:
            locator = Nominatim(user_agent="myGeocoder")
            coordinates = locator.geocode(storeAddress)
            lat = coordinates.latitude
            lon = coordinates.longitude
        except:
            lat = 0.00
            lon = 0.00
        locationData = {"Address:": storeAddress, "Latitude": lat, "Longitude": lon}
        
        try:
            storeStock = stock[ct].strip()
        except:
            storeStock = "Unknown Inventory Level"

        try:
            itemPrice = "$" + dollars[ct] + "." + cents[ct]
        except:
            itemPrice = "Unknown"
        
        storeData = {"Location": locationData, "Stock": storeStock, "Price": itemPrice}
        inventLevels.update( {entry.strip(): storeData} )
        ct += 1

    inventoryByStore.update( {store: inventLevels})

    return inventoryByStore

@app.route('/searchBy', methods=['GET'])
def searchBy():
  method = request.args.get('method')
  store = request.args.get('store')
  itemCode = request.args.get('itemCode')
  zipCode = request.args.get('zipCode')
  print("API Requested: " + method, store, itemCode, zipCode)

  htmlRequested = fetchBrickseed(store, itemCode, method, zipCode)
  decodedHtml = parseHTML(store, htmlRequested)

  return jsonify(decodedHtml)

@app.route('/getStores')
def getStores():
    return render_template('getStores.html', upcStores=upcStores, skuStores=skuStores)

if __name__ == "__main__":
        app.run(host='0.0.0.0')