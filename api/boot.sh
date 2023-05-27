#! /bin/sh
# source /opt/app-root/src/env/env_v1/bin/activate
cd /BaseApi/api
gunicorn --workers 3 --threads 3 --timeout 900 --worker-class gevent -b 0.0.0.0:5000 app:app --reload --max-requests 9000 
