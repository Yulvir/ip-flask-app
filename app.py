from flask import Flask
from flask_cors import CORS
from flask import Response

from geolite2 import geolite2
app = Flask(__name__)
from flask import request


app = Flask(__name__)
CORS(app)
@app.route('/')
def ip_geolocator():
    ip = request.args.get('ip')
    reader = geolite2.reader()
    try:

        match = reader.get(ip)
    except ValueError as e:
        print(e)
    print('My IP info:', match["country"])
    return match

@app.route('/bad')
def bad():
    reader = geolite2.reader()
    match = reader.get('1-23123')
    print('My IP info:', match["country"])
    return match


if __name__ == '__main__':
    app.run()
