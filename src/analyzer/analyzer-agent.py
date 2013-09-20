import logging
import time
import sys
from os import getpid
from os.path import dirname, abspath, isdir
from daemon import runner

# add the shared settings file to namespace
sys.path.insert(0, dirname(dirname(abspath(__file__))))
import settings

from analyzer import Analyzer
from storage.storage_mysql import StorageMysql

class AnalyzerAgent():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = settings.LOG_PATH + '/analyzer.log'
        self.stderr_path = settings.LOG_PATH + '/analyzer.log'
        self.pidfile_path = settings.PID_PATH + '/analyzer.pid'
        self.pidfile_timeout = 5

    def run(self):
        logger.info('starting skyline analyzer')
        storage = StorageMysql(
            settings.STORAGE_MYSQL_HOST,
            settings.STORAGE_MYSQL_USER,
            settings.STORAGE_MYSQL_PASS,
            settings.STORAGE_MYSQL_DB)
        Analyzer(getpid(), storage).start()

        while 1:
            time.sleep(100)

if __name__ == "__main__":
    """
    Start the Analyzer agent.
    """
    if not isdir(settings.PID_PATH):
        print 'pid directory does not exist at %s' % settings.PID_PATH
        sys.exit(1)

    if not isdir(settings.LOG_PATH):
        print 'log directory does not exist at %s' % settings.LOG_PATH
        sys.exit(1)


    analyzer = AnalyzerAgent()

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s :: %(name)s :: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(settings.LOG_PATH + '/analyzer.log')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        analyzer.run()
    else:
        daemon_runner = runner.DaemonRunner(analyzer)
        daemon_runner.daemon_context.files_preserve=[handler.stream]
        daemon_runner.do_action()
