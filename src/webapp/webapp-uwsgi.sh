#!/bin/sh

# see: http://projects.unbit.it/uwsgi/wiki/Doc
#export UWSGI_SOCKET=0.0.0.0:7273
export UWSGI_SOCKET=/tmp/skyline-uwsgi.sock
# enable the master process
export UWSGI_MASTER=1
# load the applications after each worker’s fork(), 
# changes the way graceful reloading works: instead of
# reloading the whole instance, each worker is reloaded in chain
export UWSGI_LAZY=1
# interval (in seconds) of master checks
export UWSGI_CHECK_INTERVAL=120
#procname-prefix = spark
# number of worker processes
export UWSGI_PROCESSES=8
# internal buffer size for uwsgi packet parsing
export UWSGI_BUFFER_SIZE=65536
# enable python threads
#enable-threads = true
# request that will take longer than the seconds specified
# in the harakiri timeout will be dropped
#harakiri = 120
#harakiri-verbose = true
# limit the size of body in HTTP requests
#limit-post = 65536
# save to disk all HTTP body bigger than the limit specified
#post-buffering = 8192
# run the processes in background using a logfile or a udp server
export UWSGI_DAEMONIZE=/var/log/skyline-uwsgi.log
export UWSGI_PIDFILE=/var/run/skyline-uwsgi.pid
# socket listen queue (default: 100), requests waiting for a process to became ready
# set kernel param first: echo 4096 > /proc/sys/net/core/somaxconn
export UWSGI_LISTEN=4096
# maximum number of requests - when a worker reaches this number it will get recycled
#max-requests = 0
# recycle a worker when its address space usage is over the limit specified
#reload-on-as = 0
# recycle a worker when its physical unshared memory is over limit specified
#reload-on-rss = 0
# automatically kill workers without a master process
#no-orphans = true
# log requests slower than the specified number of milliseconds
export UWSGI_LOG_SLOW=10000
# 50 mb
export UWSGI_LOG_MAXSIZE=52428800
# disable request logging - generates too much data
export UWSGI_DISABLE_LOGGING=true

export UWSGI_VIRTUALENV=/usr/local/skyline/env
export UWSGI_PYTHONPATH=/usr/local/skyline/skyline/src/webapp
# flask entry point
export UWSGI_MODULE=webapp
export UWSGI_CALLABLE=app

exec /usr/local/skyline/env/bin/uwsgi
