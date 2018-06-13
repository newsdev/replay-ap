import os

##
## Basic app settings
##
DEBUG = False
HOST = '0.0.0.0'
ADM_PORT = 8000
PUB_PORT = 8001
PUB_URL = 'localhost.newsdev.net:%s' % PUB_PORT
ADM_URL = 'localhost.newsdev.net:%s' % ADM_PORT


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
STORAGE_BUCKET = os.environ.get('REPLAY_AP_BUCKET', 'int.stg.nyt.com')
BASE_DIR = os.environ.get('REPLAY_AP_BASE_DIR', 'replay-ap/')

##
## Spreadsheet credentials for reading from google sheet for calendar.
##
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SERVICE_ACCOUNT_FILE = os.environ.get('REPLAY_AP_CREDS', 'credentials.json')
SHEETID = os.environ.get('REPLAY_AP_CALENDAR_SHEETID', '')
RANGE = os.environ.get('REPLAY_AP_CALENDAR_RANGE', '')

