import os

from config.dev.settings import *

PUB_URL = 'https://replay-ap.newsdev.nytimes.com/'
ADM_URL = 'https://replay-ap.newsdev.nyt.net/
ADM_PORT = 8000
PUB_PORT = ADM_PORT

STORAGE_BUCKET = os.environ.get('REPLAY_AP_BUCKET', 'int.nyt.com')
DEBUG = False