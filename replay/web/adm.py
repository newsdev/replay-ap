import argparse
import datetime
import glob
import json
import os
import random
import re

from flask import Flask, render_template, request, make_response
from google.cloud import storage
import redis
import requests

from replay import utils

BASE_DIR = os.environ.get('REPLAY_AP_BASE_DIR', 'replay-ap/')
RATELIMITED_HEADERS = {"Connection": "keep-alive","Content-Length": 199,"Content-Type": "text/xml","Date": "Fri, 29 Jan 2017 16:54:17 GMT","Server": "Apigee Router"}
ERRORMODE_HEADERS = {"Connection": "keep-alive","Content-Type": "text/json","Date": "Fri, 29 Jan 2017 16:54:17 GMT","Server": "Apigee Router"}
RATELIMITED_STRING = """
<Error xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
<Code>403</Code>
<Message>Over quota limit.</Message>
<link href="https://developer.ap.org/api-console" rel="help"/>
</Error>
"""

r_conn = redis.StrictRedis(
    host=os.environ.get('REPLAY_AP_REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REPLAY_AP_REDIS_PORT', 6379)), 
    db=int(os.environ.get('REPLAY_AP_REDIS_DB', 0)),
    password = os.environ.get('REPLAY_AP_REDIS_PASS', '')
)

app = Flask(__name__)

def is_elec(e, file_path):
    try:
        file_path = file_path.split('/national/')[1]
        if e in file_path:
            return True
    except:
        pass
    return False

@app.route('/healthcheck')
def healthcheck():
    return "200 ok"

@app.route('/recording/<racedate>/<action>/')
def recording(racedate, action):
    message = "Something bad happened that didn't trigger either start/stop action."
    success = False

    if action == "start":
        active, err = utils.get_active_recordings()
        matching_active_recordings = []
        for a in active:
            if "record-ap-%s" % racedate == a['name']:
                have_active_recording = True
                matching_active_recordings.append(a['name'])

        if len(matching_active_recordings) > 0:
            for r in matching_active_recordings:
                # already running
                message = "[PM2][ERROR] Process %s already running" % r
        else:
            ##
            ## Actual recording abstracted out
            ##
            out, err = utils.start_recording(racedate)

            if err:
                # error starting the recording
                message = err.decode('utf-8').replace('\n')
            else:
                # success!
                message = "[PM2][INFO] Process replay-ap-%s started" % racedate
                success = True
    
    if action == "stop":
        ##
        ## Actual stop process abstracted out
        ##
        out,err = utils.stop_recording(racedate)

        if err:
            # error stopping the recording.
            message = err.decode("utf-8").replace('\n','')
        else:
            # success!
            message = "[PM2][INFO] Process record-ap-%s stopped" % racedate
            success = True

    print(message)
    return json.dumps({"success": success, "message": message})

@app.route('/')
def index():
    bucket = utils.get_bucket()

    completed_recordings = utils.get_completed_recordings(bucket)
    elections = utils.get_racedates(bucket)
    active_recordings, err = utils.get_active_recordings()

    if len(active_recordings) > 0:
        active_recordings = [a['name'] for a in active_recordings]

    context = utils.build_context()

    context['past'] = []
    context['current'] = []
    context['future'] = []

    for e in elections:
        for level in ['national']:
            positions = [b.public_url.split(BASE_DIR)[1] for b in completed_recordings if is_elec(e, b.public_url.split(BASE_DIR)[1])]
            national = True
            e_dict = {}
            election_key = 'REPLAY_AP_%s' % e
            e_dict['status'] = False
            if "record-ap-%s" % e in active_recordings:
                e_dict['status'] = True
            e_dict['racedate'] = e
            e_dict['national'] = national
            e_dict['level'] = level
            e_dict['title'] = "%s [%s]" % (e, level)
            e_dict['position'] = int(r_conn.get(election_key + '_POSITION') or 0)
            e_dict['total_positions'] = len(positions)
            e_dict['playback'] = int(r_conn.get(election_key + '_PLAYBACK') or 1)
            e_dict['errormode'] = utils.to_bool(r_conn.get(election_key + '_ERRORMODE'))
            e_dict['ratelimited'] = utils.to_bool(r_conn.get(election_key + '_RATELIMITED'))

            if utils.is_current(e):
                context['current'].append(e_dict)

            elif utils.is_future(e):
                context['future'].append(e_dict)

            else:
                context['past'].append(e_dict)

    context['past'] = sorted(context['past'], key=lambda x:x['racedate'], reverse=True)

    return render_template('index.html', **context)