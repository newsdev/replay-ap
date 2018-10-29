import argparse
import datetime
import glob
import importlib
import json
import os
import random
import re

from flask import Flask, render_template, request, make_response, Response, redirect
from google.cloud import storage
import requests

from replay import utils

settings = importlib.import_module('config.%s.settings' % os.environ.get('DEPLOYMENT_ENVIRONMENT', 'dev'))

r_conn = settings.REDIS_CONNECTION

app = Flask(__name__)

@app.route('/healthcheck', methods=['GET'])
def health():
    return Response('ok')

@app.route('/', methods=['GET'])
def index():
    user = request.args.get('user', 'staging')        

    bucket = utils.get_bucket()

    completed_recordings = utils.get_completed_recordings(bucket, racedate='-')
    elections = utils.get_racedates(bucket)
    active_recordings, err = utils.get_active_recordings()

    if len(active_recordings) > 0:
        active_recordings = [a['name'] for a in active_recordings]

    context = utils.build_context()
    context['user'] = user
    context['available_users'] = list(set([k.decode('utf-8').split('_REPLAY_AP')[0] for k in r_conn.keys(pattern="*_REPLAY_AP_*_POSITION")]))

    context['past'] = []
    context['current'] = []
    context['future'] = []

    for e in elections:
        positions = [b.public_url.split(settings.BASE_DIR)[1] for b in completed_recordings if e in b.public_url]
        national = True
        e_dict = {}
        election_key = '%s_REPLAY_AP_%s' % (user, e)
        e_dict['status'] = False
        if "record-ap-%s" % e in active_recordings:
            e_dict['status'] = True
        e_dict['racedate'] = e
        e_dict['national'] = national
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

@app.route('/recording/<racedate>/<action>/')
def recording(racedate, action):
    message = "Something bad happened that didn't trigger either start/stop action."
    success = False

    user = request.args.get('user', 'staging')        

    if action == "position":
        election_key = '%s_REPLAY_AP_%s' % (user, racedate)
        if request.args.get('errormode', None):
            if request.args.get('errormode', None) == 'true':
                r_conn.set(election_key + '_ERRORMODE', 'True')

            if request.args.get('errormode', None) == 'false':
                r_conn.set(election_key + '_ERRORMODE', 'False')

        if request.args.get('ratelimited', None):
            if request.args.get('ratelimited', None) == 'true':
                r_conn.set(election_key + '_RATELIMITED', 'True')

            if request.args.get('ratelimited', None) == 'false':
                r_conn.set(election_key + '_RATELIMITED', 'False')

        if request.args.get('playback', None):
            try:
                playback = abs(int(request.args.get('playback', None)))
            except ValueError:
                return json.dumps({
                        'error': True,
                        'error_type': 'ValueError',
                        'message': 'playback must be an integer greater than 0.'
                    })
            r_conn.set(election_key + '_PLAYBACK', str(playback))

        if request.args.get('position', None):
            try:
                position = abs(int(request.args.get('position', None)))
            except ValueError:
                return json.dumps({
                        'error': True,
                        'error_type': 'ValueError',
                        'message': 'position must be an integer greater than 0.'
                    })
            r_conn.set(election_key + '_POSITION', str(position))
        message = "Set position or playback."

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

    return utils.make_ap_response(json.dumps({"success": success, "message": message}))

@app.route('/elections/<racedate>/status')
def status(racedate):
    """
    The route /<racedate>/status will return the status of a given
    election date test, including the current position in the hopper, the
    playback speed, and the path of the file that will be served at the current
    position.
    """
    user = request.args.get('user', 'staging')        

    LEVEL = 'national'
    if request.args.get('national', None):
        if request.args['national'].lower() == 'false':
            LEVEL = 'local'

    election_key = '%s_REPLAY_AP_%s' % (user, racedate)

    bucket = utils.get_bucket()
    completed_recordings = utils.get_completed_recordings(bucket, racedate)
    if len(completed_recordings) == 0:
        return make_response(json.dumps({"status": 500, "error": True}), 500, settings.ERRORMODE_HEADERS)

    sd = datetime.datetime.now() + datetime.timedelta(0, 60)

    hopper = sorted([(b.public_url, b) for b in completed_recordings], key=lambda x:x[0])        

    position = int(r_conn.get(election_key + '_POSITION') or 0)
    playback = int(r_conn.get(election_key + '_PLAYBACK') or 1)
    errormode = utils.to_bool(r_conn.get(election_key + '_ERRORMODE'))
    ratelimited = utils.to_bool(r_conn.get(election_key + '_RATELIMITED'))

    resp = make_response(json.dumps({
                'playback': playback,
                'position': position,
                'errormode': errormode,
                'ratelimited': ratelimited,
                'file': hopper[position-1][0],
                'level': LEVEL,
                'user': user
            }), 200)
    resp.headers['Content-Type'] = "application/json; charset=utf-8"
    return resp

@app.route('/elections/<racedate>')
def replay(racedate):
    user = request.args.get('user', 'staging')        
    national = True
    if request.args.get('national', None):
        if request.args['national'].lower() == 'false':
            national = False
    return utils.get_replay_file(racedate, national=national, user=user)

if __name__ == '__main__':
    app.run(host=settings.HOST, port=settings.ADM_PORT, debug=settings.DEBUG)