import logging
import time

import settings

LOG = logging.getLogger(__name__)

class Alerter(object):
    
    def __init__(self, storage):
        self.storage = storage
        self.cache = {}

    def add(self, anomaly):
        now = time.time()
        
        value = anomaly[0]
        metric_name, host_name = self.__split_metric(anomaly[1])
        ts = anomaly[2]
        
        alert = self.cache.get(host_name)
        if alert is None:
            #  0          1             2       3
            # [anomalies, anomalies_ts, config, config_ts]
            alert = [[], None, {}, None]
            self.cache[host_name] = alert
        
        if alert[3] is None or alert[3] + settings.ALERT_CONFIG_TIME <= now:
            alert[2] = self.storage.get_alert_config(host_name)
            alert[3] = now
        
        if metric_name not in alert[2]:
            alert[0].append((host_name, metric_name, ts, value))
            if alert[1] is None:
                # start aggregation window
                alert[1] = now

    def __split_metric(self, metric):
        i = metric.rfind('@')
        return metric[:i], metric[i+1:]
    
    def send_alerts(self):
        now = time.time()
        expired = []
        for key, alert in self.cache.iteritems():
            if alert[1] is not None and alert[1] + settings.ALERT_AGGREGATE_TIME <= now:
                LOG.info("Sending alert: %s", alert)
                # TODO
                
                # empty anomalies aggregator
                alert[0] = []
                alert[1] = None
            if alert[1] is None \
                    and (alert[3] is None or alert[3] + settings.ALERT_CONFIG_TIME <= now):
                expired.append(key)
        for key in expired:        
            del self.cache[key]
