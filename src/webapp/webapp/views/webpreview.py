import logging
import redis
import simplejson as json
from msgpack import Unpacker
from flask import request, render_template

import settings
from webapp import app

LOG = logging.getLogger(__name__)

REDIS_CONN = redis.StrictRedis(unix_socket_path=settings.REDIS_SOCKET_PATH)

@app.route("/")
def index():
    return render_template('index.html'), 200

@app.route("/app_settings")
def app_settings():
    app_settings = {'GRAPHITE_HOST': settings.GRAPHITE_HOST,
                    'OCULUS_HOST': settings.OCULUS_HOST,
                    'MINI_NAMESPACE': settings.MINI_NAMESPACE,
                    'FULL_NAMESPACE': settings.FULL_NAMESPACE
                   }
    resp = json.dumps(app_settings)
    return resp, 200

@app.route("/api", methods=['GET'])
def data():
    metric = request.args.get('metric', None)
    try:
        raw_series = REDIS_CONN.get(metric)
        if not raw_series:
            resp = json.dumps({'results': 'Error: No metric by that name'})
            return resp, 404
        else:
            unpacker = Unpacker(use_list = False)
            unpacker.feed(raw_series)
            timeseries = [item[:2] for item in unpacker]
            resp = json.dumps({'results': timeseries})
            return resp, 200
    except Exception as e:
        error = "Error: " + e
        resp = json.dumps({'results': error})
        return resp, 500
