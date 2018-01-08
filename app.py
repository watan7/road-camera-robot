#Loading Dependencies
from __future__ import print_function
from future import standard_library
standard_library.install_aliases()


from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import json
import os
import requests 

from flask import Flask
from flask import request
from flask import make_response


#Receiving HTTP Request
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    
    if req.get("result").get("action") == "Road_Camera_Call":
        camera_title = camera_title_generate(req)
        print("Request:")
        print(json.dumps(req, indent=4))
        res = processRequest(req, camera_title)    
        res = json.dumps(res, indent=4)

    elif req.get("originalRequest").get("data").get("postback").get("payload") == "FACEBOOK_LOCATION":
        coordinates = req.get("originalRequest").get("data").get("postback").get("data")
        user_coordinates = use_stopFinder_API(coordinates)       
        res = makeWebhookResult_stopFinder(user_coordinates)
        res = json.dumps(res, indent=4)
        
    else:
        res = "nothing was returned "
        res = json.dumps(res, indent=4)
    
    # print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

#returns title name of camera
def camera_title_generate(req):
    if req.get("result").get("action") != "Road_Camera_Call":
        return {}

    result = req.get("result")
    parameters = result.get("parameters")
    camera_title = parameters.get("camera_title")
    if camera_title is None:
        return {}
    return camera_title

#Loads data from Live Cameras API - Transport NSW and Makes webhook result
def processRequest(req, camera_title):
    baseurl = "https://api.transport.nsw.gov.au/v1/live/cameras"
    response = requests.get(baseurl, headers={'Authorization': 'apikey pYIdffDyBMqdtActEnbbBcajSC3gEBdTkAtx'})
    data = response.json()
    res = makeWebhookResult(data, camera_title)
    return res

#Makes result sent to DialogueFlow
def makeWebhookResult(data, camera_title):
    
    data1 = data['features'][0:]
    titles = []
    for index in data1:
        titles.append(index['properties']['title'])
    index = titles.index(camera_title)   

    features = data.get('features')
    if features is None:
        return {}

    camera = features[index]
    if camera is None:
        return {}

    properties = camera.get('properties')
    if properties is None:
        return {}

    href = properties.get('href')
    if href is None:
        return {}

    # print(json.dumps(item, indent=4))

    speech = "Here is a photo of the traffic in "

    print("Response:")
    print(speech, camera_title, href)

    return {
        "speech": speech + camera_title + href, 
        "displayText": speech,
        # "data": data,
        # "contextOut": [],
        "source": "Road_Camera_Robot"
    }

#Creates JSON from Coord_API
def use_stopFinder_API(location_data):
    #Process coordinates data
    coord = '{0:01.6f}:{1:01.6f}:EPSG:4326'.format(location_data["long"], location_data["lat"])
    radius = 1000

    api_Endpoint = 'https://api.transport.nsw.gov.au/v1/tp/'
    api_Call = 'coord'
    api_Parameters = {
        "outputFormat": "rapidJSON",
        "coord": coord,
        "coordOutputFormat": "EPSG:4326",
        "inclFilter": 1,
        "type_1": "GIS_POINT",
        "radius_1": radius,
        "PoisOnMapMacro": "true",
        "version": "10.2.1.42",
        "inclDrawClasses_1": 74,
        }

    baseurl = api_Endpoint + api_Call + "?"
    response = requests.get(baseurl, params=api_Parameters, headers={'Authorization': 'apikey pYIdffDyBMqdtActEnbbBcajSC3gEBdTkAtx'})
    data = response.json()
    
    return data

def makeWebhookResult_stopFinder(data):
    
    data1 = data["locations"]
    names = []
    lat = []
    long = []
    distance = []

    for index in data1:
        names.append(index["name"])
        lat.append(index["coord"][0])
        long.append(index["coord"][1])
        distance.append(index["properties"]["distance"])
        
        speech = []
        
    for i in range(len(names)):
        speech.append("{}: {} is {}m away - https://www.google.com/maps/search/?api=1&query={},{}".format(i + 1, names[i], distance[i], lat[i], long[i]))
    
    speech = ' '.join(speech)
        
    return {
        "speech": speech, 
        "displayText": speech,
        # "data": data,
        # "contextOut": [],
        "source": "Road_Camera_Robot",
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')
