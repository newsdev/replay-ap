import os

import redis

##
## Basic app settings
##
DEBUG = False
HOST = '0.0.0.0'
ADM_PORT = 8000
PUB_PORT = 8001
PUB_URL = 'http://localhost.newsdev.net:%s' % PUB_PORT
ADM_URL = 'http://localhost.newsdev.net:%s' % ADM_PORT


##
## Strings / headers for impersonating the AP.
##
RATELIMITED_HEADERS = {"Connection": "keep-alive","Content-Length": 199,"Content-Type": "text/xml","Date": "Fri, 29 Jan 2017 16:54:17 GMT","Server": "Apigee Router"}
ERRORMODE_HEADERS = {"Connection": "keep-alive","Content-Type": "text/json","Date": "Fri, 29 Jan 2017 16:54:17 GMT","Server": "Apigee Router"}
RATELIMITED_STRING = """
<Error xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
<Code>403</Code>
<Message>Over quota limit.</Message>
<link href="https://developer.ap.org/api-console" rel="help"/>
</Error>
"""

##
## Bucket auth for persisting recorded files and reading files.
##
STORAGE_BUCKET = os.environ.get('REPLAY_AP_BUCKET', 'int.nyt.com')
BASE_DIR = os.environ.get('REPLAY_AP_BASE_DIR', 'apps/replay-ap')

##
## Spreadsheet credentials for reading from google sheet for calendar.
##
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SERVICE_ACCOUNT_FILE = os.environ.get('REPLAY_AP_CREDS', 'credentials.json')
SHEETID = os.environ.get('REPLAY_AP_CALENDAR_SHEETID', '')
RANGE = os.environ.get('REPLAY_AP_CALENDAR_RANGE', '')

##
## REDIS
##
REDIS_CONNECTION = redis.StrictRedis(
    host=os.environ.get('REPLAY_AP_REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REPLAY_AP_REDIS_PORT', 6379)), 
    db=int(os.environ.get('REPLAY_AP_REDIS_DB', 0)),
    password = os.environ.get('REPLAY_AP_REDIS_PASS', '')
)