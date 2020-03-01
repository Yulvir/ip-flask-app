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
import requests
from bs4 import BeautifulSoup
import pymongo  # package for working with MongoDB
from bson import json_util #somewhere
import json
app = Flask(__name__)
from flask import abort, jsonify
import bjoern
import datetime

import time
import atexit

from apscheduler.schedulers.background import BackgroundScheduler

# Get the first 5 hits for "google 1.9.1 python" in Google Pakistan
from googlesearch import search
from urllib.parse import urlencode, urlparse, parse_qs

from lxml.html import fromstring
from requests import get

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







def strim_for_mongo(name):
    return name.replace('.', '_').replace(':', '_').replace('-', '_')


def detect_names(name):

    list_keys = ["description", "author", "title", "article", "date", "image"]
    if any([l in name  for l in list_keys]):
        return True
    else:
        return False
def get_meta(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text)

    metas = soup.find_all('meta')
    meta_list = []
    for meta in metas:
        meta_attrs = meta.attrs
        if "name" in meta_attrs and "content" in meta_attrs:
                if detect_names(meta_attrs["name"]):
                    meta_list.append({strim_for_mongo(meta_attrs["name"]): meta_attrs["content"]})


    return meta_list


def crawl(**kwargs):
    results = []

    for rank, url in enumerate(search(kwargs["phrase"], tld='com', lang='es', stop=5)):
        results.append(dict(date=datetime.datetime.utcnow().strftime("%Y%m%dT%H:%M:%S"), n_important=str(rank), meta_urls=get_meta(url), url=url))

    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["newsdb"]
    customers = db["news"]

    x = customers.insert_many(results)
    # print list of the _id values of the inserted documents:
    print(x.inserted_ids)
    # Dump loaded BSON to valid JSON string and reload it as dict
    page_sanitized = json.loads(json_util.dumps(results))
    return page_sanitized


@ns.route('/crawler')
class Crawler(Resource):

    @api.response(200, 'catches file for internet speed measure')
    def post(self):
        return crawl(kwargs=request.get_json())

@ns.route('/news')
class News(Resource):

    @api.response(200, 'Get News from MongoDB')
    def get(self):

        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["newsdb"]
        customers = db["news"]

        x = customers.find().sort([('_id', pymongo.DESCENDING )]).limit(100)
        results = [json.loads(json_util.dumps(elem)) for elem in x]

        # print list of the _id values of the inserted documents:

        # Dump loaded BSON to valid JSON string and reload it as dict
        return results

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
    scheduler = BackgroundScheduler()
    phrase = dict(phrase="Articles about Ip or VPN ")
    scheduler.add_job(crawl, kwargs=phrase, trigger="interval", seconds=3600)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

    bjoern.run(app, host='0.0.0.0', port=5000)


    # Shut down the scheduler when exiting the app

