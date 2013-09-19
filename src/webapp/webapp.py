import redis
import logging
import simplejson as json
import sys
from msgpack import Unpacker
from flask import Flask, request, render_template
from daemon import runner
from os.path import dirname, abspath


# add the shared settings file to namespace
sys.path.insert(0, dirname(dirname(abspath(__file__))))
import settings
from storage.storage_mysql import StorageMysql

REDIS_CONN = redis.StrictRedis(unix_socket_path=settings.REDIS_SOCKET_PATH)

app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True

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

storage = StorageMysql(settings.STORAGE_MYSQL_HOST, settings.STORAGE_MYSQL_USER,
            settings.STORAGE_MYSQL_PASS, settings.STORAGE_MYSQL_DB)

@app.route("/api/anomalies", methods=['GET'])
def anomalies():
    host = request.args.get('host')
    if not host:
        resp = json.dumps({'results': 'Error: Host param is required'})
        return resp, 400
    page = request.args.get('page', 0)
    limit = request.args.get('limit', 50)
    anomalies = storage.get_anomalies(host, page, limit)
    return json.dumps(anomalies)

class App():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = settings.LOG_PATH + '/webapp.log'
        self.stderr_path = settings.LOG_PATH + '/webapp.log'
        self.pidfile_path =  settings.PID_PATH + '/webapp.pid'
        self.pidfile_timeout = 5

    def run(self):

        logger.info('starting webapp')
        logger.info('hosted at %s' % settings.WEBAPP_IP)
        logger.info('running on port %d' % settings.WEBAPP_PORT)

        app.run(settings.WEBAPP_IP, settings.WEBAPP_PORT)

if __name__ == "__main__":
    """
    Start the server
    """

    webapp = App()

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s :: %(name)s :: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(settings.LOG_PATH + '/webapp.log')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        webapp.run()
    else:
        daemon_runner = runner.DaemonRunner(webapp)
        daemon_runner.daemon_context.files_preserve=[handler.stream]
        daemon_runner.do_action()
