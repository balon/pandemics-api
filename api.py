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
supportedStores = ["walmart", "target", "lowes", "office-depot", "macys", "staples"]
last_pull_products = None
products_data = None

''' jsonify_stores(): turn supported stores into json data
        returns: json of stores by type'''
def jsonify_stores():
    return {"stores": supportedStores}

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
def parse_HTML(store, results, itemID, itemType):
    inventoryByStore = {}       # master list for storinng data
 
    if results is None:
        return None

    # parse out store information and stock information    
    tree = html.fromstring(str(results))
    storeName = tree.xpath('//strong[@class="address-location-name"]/text()')
    address = tree.xpath('//address[@class="address"]/text()')
    stock = tree.xpath('//span[@class="availability-status-indicator__text"]/text()')
    dollars = tree.xpath('//span[@class="price-formatted__dollars"]/text()')
    cents = tree.xpath('//span[@class="price-formatted__cents"]/text()')

    ct = 0
    stores = []
    for entry in storeName:
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
        
        locationData = {"Address": storeAddress, "Latitude": lat, "Longitude": lon}
        
        try:
            storeStock = stock[ct].strip()
        except:
            storeStock = "Unknown Inventory Level"

        try:
            itemPrice = "$" + dollars[ct] + "." + cents[ct]
        except:
            itemPrice = "Unknown"
        
        storeData = {"Name": entry.strip(), "Location": locationData, "Stock": storeStock, "Price": itemPrice}
        stores.append({"store": storeData})
        ct += 1

    inventoryByStore.update( {"stores": stores, "store_type": store, "itemID": itemID, "itemType": itemType})
    return {"inventory": inventoryByStore}


''' pull_products(): fetch products from google
        returns: pandas df of products'''
def pull_products():
    # caching
    global last_pull_products
    global products_data

    if last_pull_products == None:
        last_pull_products = time.time()
    else:
        current_time = time.time()
        print(current_time - last_pull_products)

        # check for new products every 6 hours
        if ((current_time - last_pull_products) < 21600):
            print("[ProductAPI] Used cache for products")
            return products_data
    
        last_pull_products = current_time
    print("[ProductAPI] Downloaded fresh products data")
    
    r = requests.get('https://docs.google.com/spreadsheets/d/e/2PACX-1vRe_QmwymRZxRRwBaaBnJ4fbAqRxPxvznAwX0Of30eZC9bH93DaxoyRfNzUL5LMRSBiju47eFQHR_om/pubhtml/sheet?headers=false&gid=951415249&single=true&range=B:E')
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
        rows.append((product_names, product_categories, product_details, product_upcs))

    products_data = pd.DataFrame(rows, columns=df_columns)
    return products_data

''' format_text: format the string
        text: string
        returns: formatted string'''
def format_text(text):
    if "misc" in text:
        text = text.replace('_misc', ' ').title() + '(Misc)'
        
        if "_" in text:
            text = ' '.join(text.split('_'))
    elif "_" in text:
        text = ' '.join(text.split('_')).title()
        
        if " N " in text:
            text = text.replace(' N ', ' & ')
    else:
        text = text.title()

    return text

''' product_details: return json of products and brands
        products: df
        returns: json data'''
def product_details(products):
    product_details = []
    for details in products.groupby(['product_category']):
        category = details[0]
        fcategory = format_text(category)

        brand_details = []
        for brand in details[1]['product_brand'].unique():
            fbrand = format_text(brand) 
            brand_details.append({"brand_details": {"brand": brand, "f_brand": fbrand}})

        category_details = {"category": category,"f_category": fcategory}        
        product_details.append({"details": {"category_details": category_details, "brands": brand_details}})
    return {"product_details": product_details}
    

''' product_list: return json of products from category and brand
        df: df
        category: the category to search for
        brand: the brand to search for
        returns: json data'''
def product_list(df, category, brand):
    df = df[(df['product_category'] == category) & (df['product_brand'] == brand)]
    
    products = []
    for product in df.iterrows():
        product = product[1]
        product_details = {"Name": product['product_name'], "UPC": product['product_upc']}
        products.append({"product": product_details})
    
    return {"product_list": {"category": category, "brand": brand, "products": products}}



''' Flask Handling '''
@app.route('/searchInventory', methods=['GET'])
def searchInventory():
  method = request.args.get('method')
  store = request.args.get('store')
  itemCode = request.args.get('itemCode')
  zipCode = request.args.get('zipCode')
  print("InventoryAPI Requested: " + method, store, itemCode, zipCode)

  htmlRequested = fetch_brickseed(store, itemCode, method, zipCode)
  decodedHtml = parse_HTML(store, htmlRequested, itemCode, method)
  return jsonify(decodedHtml)

@app.route('/getStores')
def getStores():
    return jsonify(jsonify_stores())

@app.route('/searchProducts', methods=['GET'])
def searchProducts():
    category = request.args.get('category')
    brand = request.args.get('brand')
    print("ProductAPI Requested: " + category, brand)

    return jsonify(product_list(pull_products(), category, brand))

@app.route('/getProducts', methods=['GET'])
def get_products():
    return jsonify(product_details(pull_products()))

@app.route('/loaderio-02bef853ecf78d8b5bf4cb631636e5a3/')
def loader():
    return render_template('loaderio-02bef853ecf78d8b5bf4cb631636e5a3.txt')

if __name__ == "__main__":
    app.run(host='0.0.0.0')