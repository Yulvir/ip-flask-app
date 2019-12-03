from flask import Flask
from flask_cors import CORS
from flask import Response
from flask import request
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from geolite2 import geolite2
app = Flask(__name__)

CORS(app)
@app.route('/')
def ip_geolocate():
    ip = request.args.get('ip')
    reader = geolite2.reader()
    match = []
    try:
        match = reader.get(ip)
    except ValueError as e:
        print(e)
    print('My IP info:', match)
    return dict(match=match)


@app.route('/location_info', methods=['POST'])
def location_info():
    location = request.get_json()['location']
    location_str = f"{str(location['lat'])}, {str(location['lon'])}"
    geolocator = Nominatim(user_agent="location_dict")
    output = geolocator.reverse(location_str)

    tf = TimezoneFinder(in_memory=True)
    time_zone = tf.timezone_at(lng=location['lon'], lat=location['lat'])
    location_info = output.raw['address']
    location_info['time_zone'] = time_zone
    print(location_info)

    return dict(location_info=location_info)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
