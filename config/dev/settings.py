import os

import redis

from replay import to_bool

########
#### Basic app settings
########

# Controls the Flask "debug" settings.
DEBUG = True

# Controls the Flask "host" settings.
HOST = '0.0.0.0'

# At the NYT, we run an adm app and a pub app.
# The adm realm serves the homepage.
# The pub app serves the JSON files from the AP.
# However, you may want to run the whole app in a single realm.
# If this setting is "True", URLs for the JSON files will resolve
# to the adm app, and you can just run adm.py.
SINGLE_APP = to_bool(os.environ.get('REPLAY_AP_SINGLEAPP', 'False'))
ADM_PORT = 8000
PUB_PORT = 8001
ADM_URL = os.environ.get('AP_REPLAY_ADM_URL' , 'http://localhost.newsdev.net:%s' % ADM_PORT)
PUB_URL = os.environ.get('AP_REPLAY_PUB_URL', 'http://localhost.newsdev.net:%s' % PUB_PORT)

# Re-point the PUB_URL if we're just running SINGLE_APP
if SINGLE_APP:
    PUB_URL = ADM_URL

########
#### Strings / headers for impersonating the AP.
########

# These are the headers the AP transmits with a ratelimited 403.
RATELIMITED_HEADERS = {"Connection": "keep-alive","Content-Type": "text/xml","Date": "Fri, 29 Jan 2017 16:54:17 GMT","Server": "Apigee Router"}

# This is the XML response the AP transmits with a ratelimited 403.
RATELIMITED_STRING = """
<Error xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
<Code>403</Code>
<Message>Over quota limit.</Message>
<link href="https://developer.ap.org/api-console" rel="help"/>
</Error>
"""

# I haven't seen this in a while, but this is what a 500 response looks like
# from Apigee / the AP. This was a tough one to capture.
ERRORMODE_HEADERS = {"Connection": "keep-alive","Content-Type": "text/json","Date": "Fri, 29 Jan 2017 16:54:17 GMT","Server": "Apigee Router"}

########
#### Bucket auth for persisting recorded files and reading files.
########

# Bucket name for your storage bucket.
STORAGE_BUCKET = os.environ.get('REPLAY_AP_BUCKET', 'int.nyt.com')

# Directory inside the bucket where your files should live.
BASE_DIR = os.environ.get('REPLAY_AP_BASE_DIR', 'apps/replay-ap')

########
#### Spreadsheet credentials for reading from google sheet for calendar.
########

# Only necessary if you're reading from a Google sheet for the calendar.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SERVICE_ACCOUNT_FILE = os.environ.get('REPLAY_AP_CREDS', 'credentials.json')
SHEETID = os.environ.get('REPLAY_AP_CALENDAR_SHEETID', '')
RANGE = os.environ.get('REPLAY_AP_CALENDAR_RANGE', '')

########
#### Redis
########

# Required for saving state e.g., ratelimited/errormode and which position the hopper is in.
# This will be factored out of a future version.
REDIS_CONNECTION = redis.StrictRedis(
    host=os.environ.get('REPLAY_AP_REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REPLAY_AP_REDIS_PORT', 6379)), 
    db=int(os.environ.get('REPLAY_AP_REDIS_DB', 0)),
    password = os.environ.get('REPLAY_AP_REDIS_PASS', '')
)