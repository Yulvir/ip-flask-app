from flask import Flask
from flask_cors import CORS
from flask import request
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from constants import continent_mapping
from geolite2 import geolite2
from flask_restplus import Resource, Api
from flask_restplus import reqparse

app = Flask(__name__)

api = Api(app)
CORS(app)

ns = api.namespace('/', description='Geolocate things')


parser = reqparse.RequestParser()
parser.add_argument('ip', type=str, help='Ip Query')

@ns.route('/ip_info')                   #  Create a URL route to this resource
@ns.expect(parser)
class Geolocate(Resource):            #  Create a RESTful resource

    @api.response(200, 'Location Information about Ip\'s')
    def get(self):
        args = parser.parse_args()

        '''Geolocate Ip's '''
        ip = args['ip']
        reader = geolite2.reader()
        match = []
        try:
            match = reader.get(ip)
        except ValueError as e:
            print(e)
        print('My IP info:', match)
        return dict(match=match)


@ns.route('/location_info')
class LocationInfo(Resource):

    @api.response(200, 'Location Information about latitude and longitude')
    def post(self):
        '''Information from latitudes and longitudes '''

        location = request.get_json()['location']
        location_str = f"{str(location['lat'])}, {str(location['lon'])}"
        geolocator = Nominatim(user_agent="location_dict", timeout=10)
        output = geolocator.reverse(location_str)

        tf = TimezoneFinder(in_memory=True)
        time_zone = tf.timezone_at(lng=location['lon'], lat=location['lat'])
        location_info = output.raw['address']
        location_info['time_zone'] = time_zone
        print(location_info)

        country_code = location_info["country_code"]

        location_info['continent'] = continent_mapping[country_code.upper()]

        return dict(location_info=location_info)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
