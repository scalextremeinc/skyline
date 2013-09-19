import logging
import _mysql
import myconn

LOG = logging.getLogger(__name__)

class StorageMysql(object):
    
    TABLE_HOSTS = 'skyline_hosts'
    TABLE_METRICS = 'skyline_metrics'
    TABLE_ANOMALIES = 'skyline_anomalies'
    TABLE_CONFIG = 'skyline_config'
    
    def __init__(self, mysql_host, mysql_user, mysql_pass,
            mysql_db='skyline', mysql_port=3306):
        self.mysql_host = mysql_host
        self.mysql_user = mysql_user
        self.mysql_pass = mysql_pass
        self.mysql_db = mysql_db
        self.mysql_port = mysql_port
        self.host_cache = dict()
        self.metric_cache = dict()
        self.mysql = myconn.MyConn(host=self.mysql_host, port=self.mysql_port,
            user=self.mysql_user, passwd=self.mysql_pass, db=self.mysql_db)
        self.mysql.connect()

    def saveAll(self, anomalies):
        for a in anomalies:
            self.save(a)

    def save(self, anomaly):
        value = anomaly[0]
        metric_name, host_name = self.__split_metric(anomaly[1])
        ts = anomaly[2]
        hostid = self.__get_id(StorageMysql.TABLE_HOSTS, self.host_cache, host_name)
        metricid = self.__get_id(StorageMysql.TABLE_METRICS, self.metric_cache, metric_name)
        self.__insert_anomaly(hostid, metricid, value, ts)
    
    def __split_metric(self, metric):
        i = metric.rfind('@')
        return metric[:i], metric[i+1:]
    
    def __get_id(self, table, cache, value):
        id = cache.get(value)
        if id is None:
            id = self.__select_id(table, value)
            if id is None:
                id = self.__insert_id(table, value)
            cache[value] = id
        return id
    
    def __select_id(self, table, value):
        q = "SELECT id FROM %s WHERE value='%s' LIMIT 1" % (table, self.mysql.escape_string(value))
        LOG.debug(q)
        conn = self.mysql.query(q)
        result = conn.use_result()
        rows = result.fetch_row(maxrows=1)
        if rows is not None and len(rows) == 1:
            return rows[0][0]
        return None
    
    def __insert_id(self, table, value):
        q = "INSERT INTO %s(value) VALUES('%s')" % (table, self.mysql.escape_string(value))
        LOG.debug(q)
        conn = self.mysql.query(q)
        return conn.insert_id()
    
    def __insert_anomaly(self, hostid, metricid, value, ts):
        q = "INSERT INTO %s VALUES(%s, %s, %s, %s)" \
            % (StorageMysql.TABLE_ANOMALIES, hostid, metricid, value, ts)
        LOG.debug(q)
        self.mysql.query(q)
    
    def get_alert_config(self, host_name):
        hostid = self.__get_id(StorageMysql.TABLE_HOSTS, self.host_cache, host_name)
        q = "SELECT m.value FROM %s as c, %s as m WHERE c.hostid=%s AND c.metricid=m.id" \
            % (StorageMysql.TABLE_CONFIG, StorageMysql.TABLE_METRICS, hostid)
        LOG.debug(q)
        conn = self.mysql.query(q)
        result = conn.use_result()
        
        cfg = {}
        rows = result.fetch_row(maxrows=100)
        while rows is not None and len(rows):
            for row in rows:
                cfg[row[0]] = True
            rows = result.fetch_row(maxrows=100)
        
        return cfg
    
    def get_anomalies(self, host, page=0, limit=50):
        offset = page * limit
        hostid = self.__get_id(StorageMysql.TABLE_HOSTS, self.host_cache, host)
        q = "SELECT m.value, a.ts FROM %s as m, %s as a WHERE a.metricid=m.id AND hostid=%s ORDER BY ts DESC LIMIT %s OFFSET %s" \
            % (self.TABLE_METRICS, self.TABLE_ANOMALIES, hostid, limit, offset)
        LOG.debug(q)
        conn = self.mysql.query(q)
        result = conn.use_result()
        
        anomalies = []
        
        rows = result.fetch_row(maxrows=limit)
        while rows is not None and len(rows):
            for row in rows:
                anomalies.append([row[0], row[1]])
            rows = result.fetch_row(maxrows=limit)
            
        return anomalies
