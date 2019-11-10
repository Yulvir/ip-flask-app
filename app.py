from flask import Flask
from flask_cors import CORS
from flask import Response
from flask import request

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
    return match


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
