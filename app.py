from flask import Flask
from flask_cors import CORS
from flask import request
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from constants import continent_mapping
from geolite2 import geolite2
from flask_restplus import Resource, Api
from flask_restplus import reqparse
from exceptions.exceptions import IpNotFoundException
from pysummarization.nlpbase.auto_abstractor import AutoAbstractor
from pysummarization.tokenizabledoc.simple_tokenizer import SimpleTokenizer
from pysummarization.abstractabledoc.top_n_rank_abstractor import TopNRankAbstractor
from summarize import summarize
app = Flask(__name__)
from pydnsbl import DNSBLChecker
from flask import abort, jsonify

import nltk
nltk.download('stopwords')
nltk.download('punkt')


def complete_match(match):
    if "city" not in match:
        match["city"] = {}
        match["city"]["names"] = {}
        match["city"]["names"]["en"] = "nan"
    if "postal" not in match:
        match["postal"] = {}
        match["postal"]["code"] = "nan"
    return match


api = Api(app)
CORS(app)

ns = api.namespace('/', description='Geolocate things')

parser = reqparse.RequestParser()
parser.add_argument('ip', type=str, help='Ip Query')

@ns.route('/ip_info') #  Create a URL route to this resource
@ns.expect(parser)
class Geolocate(Resource): #  Create a RESTful resource

    @api.response(200, 'Location Information about Ip\'s')
    def get(self):
        args = parser.parse_args()

        '''Geolocate Ip's '''
        ip = args['ip']
        reader = geolite2.reader()
        match = None
        try:
            match = reader.get(ip)
        except ValueError as e:
            print(e)

        if match is None:
            raise IpNotFoundException("Ip {} not found".format(ip), status_code=404)

        return dict(match=complete_match(match))


@ns.route('/ip_blacklist')                   #  Create a URL route to this resource
@ns.expect(parser)
class CheckBlackList(Resource):            #  Create a RESTful resource

    @api.response(200, 'Blacklist Information about Ip\'s')
    def get(self):
        args = parser.parse_args()

        ip = args['ip']

        match = []
        checker = DNSBLChecker()
        result: DNSBLChecker = checker.check_ip(ip)

        obj = {}
        obj["detected_by"] = result.detected_by
        obj["blacklisted"] = result.blacklisted
        print('My IP info:', match)
        return dict(match=obj)

@ns.route('/location_info')
class LocationInfo(Resource):

    @api.response(200, 'Location Information about latitude and longitude')
    def post(self):
        '''Information from latitudes and longitudes '''

        location = request.get_json()
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



@ns.route('/catcher')
class LocationInfo(Resource):

    @api.response(200, 'catches file for internet speed measure')
    def post(self):
        '''Information from latitudes and longitudes '''

        return "Done!!!"

@ns.route('/summarize')
class Summarize(Resource):

    @api.response(200, 'summarizes text')
    def get(self):

        # https://github.com/despawnerer/summarize

        document = "Coronaviruses (CoV) are a large family of viruses that cause illness ranging from the common cold to more severe diseases such as Middle East Respiratory Syndrome (MERS-CoV) and Severe Acute Respiratory Syndrome (SARS-CoV). A novel coronavirus (nCoV) is a new strain that has not been previously identified in humans." + \
"Coronaviruses are zoonotic, meaning they are transmitted between animals and people.  Detailed investigations found that SARS-CoV was transmitted from civet cats to humans and MERS-CoV from dromedary camels to humans. Several known coronaviruses are circulating in animals that have not yet infected humans." + \
"Common signs of infection include respiratory symptoms, fever, cough, shortness of breath and breathing difficulties. In more severe cases, infection can cause pneumonia, severe acute respiratory syndrome, kidney failure and even death." + \
"Standard recommendations to prevent infection spread include regular hand washing, covering mouth and nose when coughing and sneezing, thoroughly cooking meat and eggs. Avoid close contact with anyone showing symptoms of respiratory illness such as coughing and sneezing."

        # Object of automatic summarization.
        auto_abstractor = AutoAbstractor()
        # Set tokenizer.
        auto_abstractor.tokenizable_doc = SimpleTokenizer()
        # Set delimiter for making a list of sentence.
        auto_abstractor.delimiter_list = [".", "\n"]
        # Object of abstracting and filtering document.
        abstractable_doc = TopNRankAbstractor()
        # Summarize document.
        result_dict = auto_abstractor.summarize(document, abstractable_doc)

        return summarize(document, 1)


@app.errorhandler(IpNotFoundException)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
