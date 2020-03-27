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
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)
CORS(app)

# supported stores to query
upcStores = ["walmart", "target", "lowes", "office-depot", "macys", "staples"]
skuStores = ["cvs", "bjs"]


''' jsonify_stores(): turn supported stores into json data
        returns: json of stores by type'''
def jsonify_stores():
    data = {"upcStores": upcStores, "skuStores": skuStores}
    return {"stores": data}

''' fetch_brickseed(): fetch inventory levels from brickSeed
        store: store name (for URL)
        itemID: upc or sku
        idType: upc or sku
        zipCode: user zipCode'''
def fetch_brickseed(store, itemID, idType, zipCode):
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


''' parse_HTML(): fetch inventory levels from brickSeed
        store: store name
        results: html table'''
def parse_HTML(store, results):
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


''' pull_products(): fetch products from google
        returns: pandas df of products'''
def pull_products():
    r = requests.get('https://docs.google.com/spreadsheets/d/e/2PACX-1vRe_QmwymRZxRRwBaaBnJ4fbAqRxPxvznAwX0Of30eZC9bH93DaxoyRfNzUL5LMRSBiju47eFQHR_om/pubhtml/sheet?headers=false&gid=951415249&single=true&range=B:F')
    soup = BeautifulSoup(r.text, 'lxml')
    tbody = soup.find('tbody')
    parsed_columns = tbody.find_all('tr')[0]

    # get column names from data source
    df_columns = []
    for column in parsed_columns.find_all('td'):
        df_columns.append(column.text)

    # get data columns from data source
    raw_rows = tbody.find_all('tr')[2:]
    rows = []
    for row in raw_rows:
        tds = row.find_all('td')
        product_names = tds[0].text
        product_categories = tds[1].text
        product_details = tds[2].text
        product_upcs = tds[3].text
        product_skus = tds[4].text
        rows.append((product_names, product_categories, product_details, product_upcs, product_skus))

    return pd.DataFrame(rows, columns=df_columns)

''' jsonify_products(): convert products df -> json
        returns: json of products'''
def jsonify_products(products):
    exit(1)

@app.route('/searchBy', methods=['GET'])
def searchBy():
  method = request.args.get('method')
  store = request.args.get('store')
  itemCode = request.args.get('itemCode')
  zipCode = request.args.get('zipCode')
  print("API Requested: " + method, store, itemCode, zipCode)

  htmlRequested = fetch_brickseed(store, itemCode, method, zipCode)
  decodedHtml = parse_HTML(store, htmlRequested)

  return jsonify(decodedHtml)

@app.route('/getStores')
def getStores():
    return jsonify(jsonify_stores())

@app.route('/getProducts', methods=['GET'])
def get_products():
    jsonify_products(pull_products)

#products = pull_products()


if __name__ == "__main__":
    app.run(host='0.0.0.0')