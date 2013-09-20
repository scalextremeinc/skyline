import redis
import logging
import simplejson as json
import sys
from msgpack import Unpacker
from flask import Flask, request, render_template
from daemon import runner
from os.path import dirname, abspath, join

# add the shared settings file's dir to python path
sys.path.insert(0, dirname(dirname(abspath(__file__))))
import settings

# import flask app
from webapp import app

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
    formatter = logging.Formatter("%(asctime)s :: %(name)s :: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(join(settings.LOG_PATH, 'webapp.log'))
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        webapp.run()
    else:
        daemon_runner = runner.DaemonRunner(webapp)
        daemon_runner.daemon_context.files_preserve=[handler.stream]
        daemon_runner.do_action()
