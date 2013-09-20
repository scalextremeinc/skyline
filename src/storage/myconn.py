import logging
import _mysql
import time

LOG = logging.getLogger(__name__)

class MyConn(object):
    """ Mysql connection wrapper supporting reconnects """
    
    def __init__(self, **mysql_args):
        self.mysql_args = mysql_args
        self.mysql = None
        self.last_connect = 0
        self.check_interval = 10

    def connect(self):
        self.mysql = _mysql.connect(**self.mysql_args)
    
    def get_conn(self):
        now = time.time()
        if self.last_connect + self.check_interval <= now:
            try:
                self.mysql.ping()
            except:
                LOG.exception('Ping failed')
                self.connect()
                self.last_connect = now
        
        return self.mysql
    
    def query(self, q):
        LOG.debug("QUERY: %s", q)
        try:
            self.mysql.query(q)
        except:
            LOG.exception('Query failed')
            self.connect()
            self.last_connect = time.time()
            self.mysql.query(q)
        
        return self.mysql
    
    def escape_string(self, s):
        return self.mysql.escape_string(s)
