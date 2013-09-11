import logging
import time

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
        
        alert = self.cache.get(anomaly[1])
        if alert is None:
            # [anomalies, anomalies_ts, config, config_ts]
            alert = [[], None, None, None]
            self.cache[anomaly[1]] = alert
        
        if alert[3] is None or alert[3] + settings.ALERT_CONFIG_TIME <= now:
            config = self.storage.get_alert_config(host_name, metric_name)
            alert[2] = config
            alert[3] = now
        
        if alert[2] is not None:
            alert[0].append((host_name, metric_name, ts, value))
            if alert[1] is None:
                # start aggregation window
                alert[1] = now

    def __split_metric(self, metric):
        i = metric.rfind('@')
        return metric[:i], metric[i+1:]
    
    def send_alerts(self):
        now = time.time()
        for key, alert in self.cache.iteritems():
            if alert[1] is not None and alert[1] + settings.ALERT_AGGREGATE_TIME <= now:
                LOG.info("Sending alert: %s", alert)
                # TODO
                
                # empty anomalies aggregator
                alert[0] = []
                alert[1] = None
            if alert[1] is None
                    and (alert[3] is None or alert[3] + settings.ALERT_CONFIG_TIME <= now):
                del self.cache[key]
