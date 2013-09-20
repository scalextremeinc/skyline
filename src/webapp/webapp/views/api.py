import logging
import time
import urllib
import urllib2
import redis
import simplejson as json
from flask import request

from monitorqueue.metric_mapper import ZabbixMetricMapper, SingleTagMapper, PerfCounterMapper

import settings
from storage.storage_mysql import StorageMysql
from webapp import app

LOG = logging.getLogger(__name__)

STORAGE = StorageMysql(
    settings.STORAGE_MYSQL_HOST,
    settings.STORAGE_MYSQL_USER,
    settings.STORAGE_MYSQL_PASS,
    settings.STORAGE_MYSQL_DB)

REDIS = redis.StrictRedis(unix_socket_path=settings.REDIS_SOCKET_PATH)

METRIC_MAPPER = ZabbixMetricMapper()
METRIC_MAPPER.add("system.run", SingleTagMapper())
METRIC_MAPPER.add("perf_counter", PerfCounterMapper())

@app.route("/api/anomalies", methods=['GET'])
def anomalies():
    host = request.args.get('host')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    if not host or not start_time or not end_time:
        resp = json.dumps({'results': 'Error: host, start_time, end_time params required'})
        return resp, 400
    anomalies = STORAGE.get_anomalies(host, int(start_time), int(end_time))
    return json.dumps(anomalies), 200

@app.route("/api/timeseries", methods=['GET'])
def timeseries():
    host = request.args.get('host')
    metric = request.args.get('metric')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    if not host or not metric or not start_time or not end_time:
        resp = json.dumps({'results': 'Error: host, metric, start_time, end_time params required'})
        return resp, 400
    
    start_time = int(start_time)
    end_time = int(end_time)
    if end_time + settings.TSDB_QUERY_CONDITION <= time.time():
        timeseries = get_data_redis(host, metric)
    else:
        timeseries = get_data_tsdb(host, metric, start_time, end_time)
    
    resp = json.dumps(timeseries)
    return resp, 200

def get_data_redis(metric):
    timeseries = []
    try:
        redis_metric = FULL_NAMESPACE + metric + '@' + host
        LOG.debug('Redis query, metric: %s', redis_metric)
        raw_series = REDIS.get(redis_metric)
        unpacker = Unpacker(use_list = False)
        unpacker.feed(raw_series)
        timeseries = [item[:2] for item in unpacker]
    except:
        LOG.exception("Failed getting data from redis")
    
    return timeseries

def get_data_tsdb(host, metric, start_time, end_time):
    metric, tags = METRIC_MAPPER.check(metric)
    if not tags:
        tags = []
    tags.append(('host', host))
    tsdb_rsp = tsdb_query(settings.TSDB_URL, metric, start_time, end_time, tags)
    timeseries = []
    for line in tsdb_rsp.split('\n'):
        item = line.split(' ')
        if len(item) >= 3:
            item[1] = int(item[1])
            try:
                item[2] = float(item[2])
            except:
                pass
            timeseries.append(item[1:3])
    
    return timeseries

def tsdb_query(url, metric, start_time, end_time=None, tags=[], aggregator='max'):
    """ http://108.166.56.222:4242/q?start=1h-ago&m=sum:agent.ping{host=A355C40052}&ascii """
    metric = [aggregator, ':', metric]
    query = {
        'start': start_time,
        'ascii': 1}
    if end_time is not None:
        query['end'] = end_time
    if tags and len(tags) > 0:
        metric.append('{')
        i = 0
        for k, v in tags:
            metric.append(k)
            metric.append('=')
            metric.append(v)
            if i < len(tags) - 1:
                metric.append(',')
            i += 1
        metric.append('}')
    query['m'] = ''.join(metric)
    
    if not url.endswith('/q') or not url.endswith('/q/'):
        url += '/q'
    
    data = urllib.urlencode(query)
    LOG.debug('Tsdb query, url: %s, query: %s, data: %s', url, query, data)
    
    request = urllib2.Request(url, data)
    response = urllib2.urlopen(request)
    
    return response.read()
