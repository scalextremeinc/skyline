import redis
import logging
import simplejson as json
import sys
from msgpack import Unpacker
from flask import Flask, request, render_template
from daemon import runner
from os.path import dirname, abspath

from monitorcommon import logutil

# add the shared settings file's dir to python path
sys.path.insert(0, dirname(dirname(dirname(abspath(__file__)))))


app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True

# import views configures flask routes
import webapp.views

logutil.setup_logger(logging.DEBUG)
