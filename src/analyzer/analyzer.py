import logging
from redis import StrictRedis
from time import time, sleep
from threading import Thread
from collections import defaultdict
from multiprocessing import Process, Manager, Lock
from msgpack import Unpacker, unpackb, packb
from os import path, kill, getpid, system
from math import ceil
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
from smtplib import SMTP
import traceback
import operator
import settings

from algorithms import run_selected_algorithm
from algorithm_exceptions import *
from alerter import Alerter

logger = logging.getLogger("AnalyzerLog")

class Analyzer(Thread):
    def __init__(self, parent_pid, storage):
        """
        Initialize the Analyzer
        """
        super(Analyzer, self).__init__()
        self.redis_conn = StrictRedis(unix_socket_path = settings.REDIS_SOCKET_PATH)
        self.daemon = True
        self.parent_pid = parent_pid
        self.current_pid = getpid()
        self.lock = Lock()
        self.exceptions = Manager().dict()
        self.anomaly_breakdown = Manager().dict()
        self.anomalous_metrics = Manager().list()
        self.storage = storage
        self.alerter = Alerter(storage)

    def check_if_parent_is_alive(self):
        """
        Self explanatory
        """
        try:
            kill(self.current_pid, 0)
            kill(self.parent_pid, 0)
        except:
            exit(0)

    def spin_process(self, i, unique_metrics):
        """
        Assign a bunch of metrics for a process to analyze.
        """
        # Discover assigned metrics
        keys_per_processor = int(ceil(float(len(unique_metrics)) / float(settings.ANALYZER_PROCESSES)))
        if i == settings.ANALYZER_PROCESSES:
            assigned_max = len(unique_metrics)
        else:
            assigned_max = i * keys_per_processor
        assigned_min = assigned_max - keys_per_processor
        assigned_keys = range(assigned_min, assigned_max)

        # Compile assigned metrics
        assigned_metrics = [unique_metrics[index] for index in assigned_keys]

        # Check if this process is unnecessary
        if len(assigned_metrics) == 0:
            return

        # Multi get series
        raw_assigned = self.redis_conn.mget(assigned_metrics)

        # Make process-specific dicts
        exceptions = defaultdict(int)
        anomaly_breakdown = defaultdict(int)

        # Distill timeseries strings into lists
        for i, metric_name in enumerate(assigned_metrics):
            self.check_if_parent_is_alive()

            try:
                raw_series = raw_assigned[i]
                unpacker = Unpacker(use_list = False)
                unpacker.feed(raw_series)
                timeseries = list(unpacker)

                anomalous, ensemble, datapoint, ts = run_selected_algorithm(timeseries)

                # If it's anomalous, add it to list
                if anomalous:
                    base_name = metric_name.replace(settings.FULL_NAMESPACE, '', 1)
                    metric = [datapoint, base_name, ts]
                    self.anomalous_metrics.append(metric)

                    # Get the anomaly breakdown - who returned True?
                    for index, value in enumerate(ensemble):
                        if value:
                            algorithm = settings.ALGORITHMS[index]
                            anomaly_breakdown[algorithm] += 1

            # It could have been deleted by the Roomba
            except AttributeError:
                exceptions['DeletedByRoomba'] += 1
            except TooShort:
                exceptions['TooShort'] += 1
            except Stale:
                exceptions['Stale'] += 1
            except Incomplete:
                exceptions['Incomplete'] += 1
            except Boring:
                exceptions['Boring'] += 1
            except:
                exceptions['Other'] += 1
                logger.info(traceback.format_exc())

        # Collate process-specific dicts to main dicts
        with self.lock:
            for key, value in anomaly_breakdown.items():
                if key not in self.anomaly_breakdown:
                    self.anomaly_breakdown[key] = value
                else:
        	        self.anomaly_breakdown[key] += value

            for key, value in exceptions.items():
                if key not in self.exceptions:
                    self.exceptions[key] = value
                else:
        	        self.exceptions[key] += value

    def send_mail(self, alert, metric):
        """
        Send an alert email to the appropriate recipient
        """
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '[skyline alert] ' + metric[1]
        msg['From'] = settings.ALERT_SENDER
        msg['To'] = alert[1]
        link = '%s/render/?width=588&height=308&target=%s' % (settings.GRAPHITE_HOST, metric[1])
        body = 'Anomalous value: %s <br> Next alert in: %s seconds <a href="%s"><img src="%s"/></a>' % (metric[0], alert[2], link, link)
        msg.attach(MIMEText(body, 'html'))
        s = SMTP('127.0.0.1')
        s.sendmail(settings.ALERT_SENDER, alert[1], msg.as_string())
        s.quit()

    def run(self):
        """
        Called when the process intializes.
        """
        while 1:
            now = time()

            # Make sure Redis is up
            try:
                self.redis_conn.ping()
            except:
                logger.error('skyline can\'t connect to redis at socket path %s' % settings.REDIS_SOCKET_PATH)
                sleep(10)
                self.redis_conn = StrictRedis(unix_socket_path = settings.REDIS_SOCKET_PATH)
                continue

            # Discover unique metrics
            unique_metrics = list(self.redis_conn.smembers(settings.FULL_NAMESPACE + 'unique_metrics'))

            if len(unique_metrics) == 0:
                logger.info('no metrics in redis. try adding some - see README')
                sleep(10)
                continue

            # Spawn processes
            pids = []
            for i in range(1, settings.ANALYZER_PROCESSES + 1):
                if i > len(unique_metrics):
                    logger.info('WARNING: skyline is set for more cores than needed.')
                    break

                p = Process(target=self.spin_process, args=(i, unique_metrics))
                pids.append(p)
                p.start()

            # Send wait signal to zombie processes
            for p in pids:
                p.join()

            # Send alerts
            #if settings.ENABLE_ALERTS:
            #    for alert in settings.ALERTS:
            #        for metric in self.anomalous_metrics:
            #            if alert[0] in metric[1]:
            #                try:
            #                    last_alert = self.redis_conn.get('last_alert.' + metric[1])
            #                    if not last_alert:
            #                        self.redis_conn.setex('last_alert.' + metric[1], alert[2], packb(metric[0]))
            #                        self.send_mail(alert, metric)
            #                except Exception as e:
            #                    logger.error("couldn't send alert: %s" % e)

            # Write anomalous_metrics to static webapp directory
            filename = path.abspath(path.join(path.dirname( __file__ ), '..', settings.ANOMALY_DUMP))
            with open(filename, 'w') as fh:
                # Make it JSONP with a handle_data() function
                anomalous_metrics = list(self.anomalous_metrics)
                anomalous_metrics.sort(key=operator.itemgetter(1))
                fh.write('handle_data(%s)' % anomalous_metrics)
            
            # process anomalous metrics
            for metric in self.anomalous_metrics:
                try:
                    last_save_key = 'last_save.%s.%s' % (metric[1], metric[2])
                    last_save = self.redis_conn.get(last_save_key)
                    if not last_save:
                        self.redis_conn.setex(last_save_key,
                            settings.STORAGE_SAVE_FREQUENCY, packb(metric[0]))
                        self.storage.save(metric)
                        if settings.ENABLE_ALERTS:
                            self.alerter.add(metric)
                except Exception as e:
                    logger.error("Failed processing anomaly, metric: %s, error: %s", metric[1], e)
            
            # send ready alerts
            self.alerter.send_alerts()

            # Log progress
            logger.info('seconds to run    :: %.2f' % (time() - now))
            logger.info('total metrics     :: %d' % len(unique_metrics))
            logger.info('total analyzed    :: %d' % (len(unique_metrics) - sum(self.exceptions.values())))
            logger.info('total anomalies   :: %d' % len(self.anomalous_metrics))
            logger.info('exception stats   :: %s' % self.exceptions)
            logger.info('anomaly breakdown :: %s' % self.anomaly_breakdown)

            # Log to Graphite
            if settings.GRAPHITE_HOST != '':
                host = settings.GRAPHITE_HOST.replace('http://', '')
                system('echo skyline.analyzer.run_time %.2f %s | nc -w 3 %s 2003' % ((time() - now), now, host))
                system('echo skyline.analyzer.total_analyzed %d %s | nc -w 3 %s 2003' % ((len(unique_metrics) - sum(self.exceptions.values())), now, host))

            # Check canary metric
            raw_series = self.redis_conn.get(settings.FULL_NAMESPACE + settings.CANARY_METRIC)
            if raw_series is not None:
                unpacker = Unpacker(use_list = False)
                unpacker.feed(raw_series)
                timeseries = list(unpacker)
                time_human = (timeseries[-1][0] - timeseries[0][0]) / 3600
                projected = 24 * (time() - now) / time_human

                logger.info('canary duration   :: %.2f' % time_human)
                if settings.GRAPHITE_HOST != '':
                    host = settings.GRAPHITE_HOST.replace('http://', '')
                    system('echo skyline.analyzer.duration %.2f %s | nc -w 3 %s 2003' % (time_human, now, host))
                    system('echo skyline.analyzer.projected %.2f %s | nc -w 3 %s 2003' % (projected, now, host))


            # Reset counters
            self.anomalous_metrics[:] = []
            self.exceptions = Manager().dict()
            self.anomaly_breakdown = Manager().dict()

            # Sleep if it went too fast
            if time() - now < 5:
                logger.info('sleeping due to low run time...')
                sleep(10)

