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

from datetime import datetime, timedelta
from pytz import timezone
import pytz

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

    elif (req.get("result").get("action") == "Train_Trip_Request"):
        search_query_departure_station_1 = req.get("result").get("parameters").get("Train_stations_departure")
        search_query_arrival_station_1 = req.get("result").get("parameters").get("Train_stations_arrival")
        stop_id_departure_1 = find_stop_id(search_query_arrival_station_1, search_query_departure_station_1, "departure_station")
        stop_id_arrival_1 = find_stop_id(search_query_arrival_station_1, search_query_departure_station_1, "arrival_station")
        train_trips_1 = trip_planner(stop_id_arrival_1, stop_id_departure_1)
        res = makeWebhookResult_trainTrip(train_trips_1)
        res = json.dumps(res, indent=4)        
        
    elif (req.get("result").get("action") == "Opal_Reseller"):
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
        "speech": speech, 
        "displayText": speech,
        "data": {
          "facebook": {
            "attachment": {
                "type": "image",
                "payload": {
                    "url": href,
              }
            }
          }
        },
        "score": 1,                  
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

    for index in data1[:5]:
        names.append(index["name"])
        lat.append(index["coord"][0])
        long.append(index["coord"][1])
        distance.append(index["properties"]["distance"])
        
        speech = []
        
    for i in range(len(names)):
        speech.append("{}: {} is {}m away - https://www.google.com/maps/search/?api=1&query={},{}\
                               \
                               ".format(i + 1, names[i], distance[i], lat[i], long[i]))
    
    speech = ''.join(speech)
        
    return {
        "speech": speech, 
        "displayText": speech,
        # "data": data,
        # "contextOut": [],
        "source": "Road_Camera_Robot",
    }

#Stop Finder API
def find_stop_id(search_query_arrival_station, search_query_departure_station, a):

    if a == "arrival_station":
        search_query = search_query_arrival_station
    elif a == "departure_station":
        search_query = search_query_departure_station
    else:
        return {}
    
    api_Endpoint = "https://api.transport.nsw.gov.au/v1/tp/"
    api_Call = "stop_finder"
    api_Parameters = {
        "outputFormat": "rapidJSON",
        "type_sf": "any",
        "name_sf": search_query,
        "coordOutputFormat": 'EPSG%3A4326',
        "TfNSWSF": "true",
        "version": "10.2.1.42"
    }

    baseurl = api_Endpoint + api_Call + "?"
    response = requests.get(baseurl, params=api_Parameters, headers={'Authorization': 'apikey pYIdffDyBMqdtActEnbbBcajSC3gEBdTkAtx'})
    
    data = response.json()
    data = data['locations']

    isBest = []
    for index in data:
        isBest.append(index['isBest'])

    index = isBest.index(True)

    stop_id = data[index].get('id')
    
    return stop_id

#Trip Planner API
def trip_planner(arrival_station_id, departure_station_id):
    api_Endpoint = "https://api.transport.nsw.gov.au/v1/tp/"
    api_Call = "trip"

    #Input Parameters for search
    when_time = datetime.now().strftime("%H%M")
    when_date = datetime.now().strftime ("%Y%m%d")
    origin = departure_station_id
    destination = arrival_station_id

    api_Parameters = {
        "outputFormat": "rapidJSON",
        "coordOutputFormat": "EPSG:4326",
        "depArrMacro": "dep",
        "itdDate": datetime.now().strftime ("%Y%m%d"),
        "itdTime": datetime.now().strftime("%H%M"),
        "type_origin": "stop",
        "name_origin": origin,
        "type_destination": "stop",
        "name_destination": destination,
        "calcNumberOfTrips": 3,
        "TfNSWSF": "true",
        "version": "10.2.1.42"
    }

    baseurl = api_Endpoint + api_Call + "?"
    response = requests.get(baseurl, params=api_Parameters, headers={'Authorization': 'apikey pYIdffDyBMqdtActEnbbBcajSC3gEBdTkAtx'})
    data = response.json()
    
    data_journeys = data.get("journeys")
    
    data_legs = []
    for index in data_journeys:
        data_legs.append(index['legs'][0])

    data_origin = []
    for index in data_legs:
        data_origin.append(index['origin'])

    data_departureTimePlanned = []
    for index in data_origin:
        data_departureTimePlanned.append(convert_time(index['departureTimeEstimated']))

    data_destination = []
    for index in data_legs:
        data_destination.append(index['destination'])

    data_arrivalTimePlanned = []
    for index in data_destination:
        data_arrivalTimePlanned.append(convert_time(index['arrivalTimeEstimated']))
    
       
    return data_departureTimePlanned, data_arrivalTimePlanned


##Convert Time function
def convert_time(dtp):
    utc = pytz.utc
    fmt = '%Y-%m-%d %H:%M'
    year = int(dtp[0:4])
    month = int(dtp[5:7])
    day = int(dtp[8:10])
    hour = int(dtp[11:13])
    minute = int(dtp[14:16])
    utc_dt = utc.localize(datetime(year, month, day, hour, minute, 0))
    au_tz = timezone('Australia/Sydney')
    au_dt = utc_dt.astimezone(au_tz)
    string = au_dt.strftime(fmt)
    return string

def makeWebhookResult_trainTrip(train_trips):
    search_query_departure_station_1 = req.get("result").get("parameters").get("Train_stations_departure")
    search_query_arrival_station_1 = req.get("result").get("parameters").get("Train_stations_arrival")
    
    speech = []
       
    for i in range(len(train_trips[0])):
        speech.append("{}: Departs {} at {} and arrives {} at {}".format(i + 1, search_query_arrival_station_1, train_trips[0][i], search_query_departure_station_1, train_trips[1][i]))
    
    speech = ''.join(speech)
    
    return {
        "speech": speech, 
        "displayText": speech,
        # "data": data,
        # "contextOut": [],
        "source": "Road_Camera_Robot"
    }





if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=True, port=port, host='0.0.0.0')
