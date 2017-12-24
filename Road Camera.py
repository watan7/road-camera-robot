from __future__ import print_function
from future.standard_library import install_aliases
install_aliases()

from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import json
import os

from flask import Flask
from flask import request
from flask import make_response

# Flask app should start in global layout
app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = processRequest(req)

    res = json.dumps(res, indent=4)
    # print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def processRequest(req):
    if req.get("result").get("action") != "Road_Camera_Call":
        return {}
    baseurl = "https://api.transport.nsw.gov.au/v1/live/cameras"
    yql_query = makeYqlQuery(req)
    if yql_query is None:
        return {}
    result = urlopen(baseurl).read()
    data = json.loads(result)
    res = makeWebhookResult(data)
    return res

data1 = data['features'][0:]
titles = []
for index in data1:
    titles.append(index['properties']['title'])
    print(index['properties']['title'])
index = titles.index(camera_title)    


def makeYqlQuery(req):
    result = req.get("result")
    parameters = result.get("parameters")
    camera_title = parameters.get("camera_title")
    if camera_title is None:
        return None

    return camera_title


def makeWebhookResult(data):
    
    features = data.get('features')
    if query is None:
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

    speech = "Here is a photo of the traffic in" + camera_title + href

    print("Response:")
    print(speech)

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

    app.run(debug=False, port=port, host='0.0.0.0')
