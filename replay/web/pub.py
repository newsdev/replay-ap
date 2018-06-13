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
import redis
import requests

from replay import utils

r_conn = redis.StrictRedis(
    host=os.environ.get('REPLAY_AP_REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REPLAY_AP_REDIS_PORT', 6379)), 
    db=int(os.environ.get('REPLAY_AP_REDIS_DB', 0)),
    password = os.environ.get('REPLAY_AP_REDIS_PASS', '')
)

settings = importlib.import_module('config.%s.settings' % os.environ.get('DEPLOYMENT_ENVIRONMENT', 'dev'))

app = Flask(__name__)

@app.route('/healthcheck', methods=['GET'])
def health():
    return Response('ok')

@app.route('/', methods=['GET'])
def index():
    return redirect(settings.ADMIN_URL)

@app.route('/elections/<racedate>')
def replay(racedate):
    """
    The route `/<racedate>` will replay the election files found in the folder
    `/<DATA_DIR>/<racedate>/`. The files should be named such that the first file
    will be sorted first in a list by `glob.glob()`, e.g., a higher letter (a) or lower
    number (0). Incrementing UNIX timestamps (such as those captured by Elex) would be
    ideal.

    This route takes two optional control parameters. Once these have been passed to set
    up an election test, the raw URL will obey the instructions below until the last
    file in the hopper has been reached.

    * `position` will return the file at this position in the hopper. So, for example,
    `position=0` would set the pointer to the the first file in the hopper and return it.

    * `playback` will increment the position by itself until it is reset. So, for example,
    `playback=5` would skip to every fifth file in the hopper.

    When the last file in the hopper has been reached, it will be returned until the Flask
    app is restarted OR a new pair of control parameters are passed.

    Example: Let's say you would like to test an election at 10x speed. You have 109
    files in your `<storage_bucket>/apps/replay-ap/<racedate>/national/` folder named 001.json through 109.json

    * Request 1: `/<racedate>?position=0&playback=10` > 001.json
    * Request 2: `/<racedate>` > 011.json
    * Request 3: `/<racedate>` > 021.json
    * Request 4: `/<racedate>` > 031.json
    * Request 5: `/<racedate>` > 041.json
    * Request 6: `/<racedate>` > 051.json
    * Request 7: `/<racedate>` > 061.json
    * Request 8: `/<racedate>` > 071.json
    * Request 9: `/<racedate>` > 081.json
    * Request 10: `/<racedate>` > 091.json
    * Request 11: `/<racedate>` > 101.json
    * Request 12: `/<racedate>` > 109.json
    * Request 13 - ???: `/<racedate>` > 109.json

    Requesting /<racedate>?position=0&playback=1 will reset to the default position
    and playback speeds, respectively.
    """

    LEVEL = 'national'
    if request.args.get('national', None):
        if request.args['national'].lower() == 'false':
            LEVEL = 'local'

    ## UGH I AM GONNA HAVE TO REIMPLEMENT THIS IN NOVEMBER.
    ## UGH UGH UGH UGH
    #
    # if request.args.get('national', None) and request.args.get('level', None):
    #     LEVEL = 'local'
    #     if request.args['national'].lower() == 'true':
    #         LEVEL = 'national'
    #     if request.args['level'] == 'district':
    #         LEVEL = 'districts'
    # else:
    #     return json.dumps({
    #         'error': True,
    #         'message': 'must specify national=true or national=false and level=ru or level=district'
    #     })

    election_key = 'REPLAY_AP_%s' % racedate

    bucket = utils.get_bucket()
    completed_recordings = utils.get_completed_recordings(bucket)
    if len(completed_recordings) == 0:
        return make_response(json.dumps({"status": 500, "error": True}), 500, settings.ERRORMODE_HEADERS)

    sd = datetime.datetime.now() + datetime.timedelta(0, 60)

    hopper = sorted([(b.public_url, b) for b in completed_recordings if utils.is_elec(racedate, b.public_url.split(settings.BASE_DIR)[1])], key=lambda x:x[0])        

    position = int(r_conn.get(election_key + '_POSITION') or 0)
    playback = int(r_conn.get(election_key + '_PLAYBACK') or 1)

    errormode = utils.to_bool(r_conn.get(election_key + '_ERRORMODE'))
    ratelimited = utils.to_bool(r_conn.get(election_key + '_RATELIMITED'))

    if request.args.get('errormode', None):
        if request.args.get('errormode', None) == 'true':
            r_conn.set(election_key + '_ERRORMODE', 'True')
            errormode = True

        if request.args.get('errormode', None) == 'false':
            r_conn.set(election_key + '_ERRORMODE', 'False')
            errormode = False

    if request.args.get('ratelimited', None):
        if request.args.get('ratelimited', None) == 'true':
            r_conn.set(election_key + '_RATELIMITED', 'True')
            ratelimited = True

        if request.args.get('ratelimited', None) == 'false':
            r_conn.set(election_key + '_RATELIMITED', 'False')
            ratelimited = False

    if request.args.get('playback', None):
        try:
            playback = abs(int(request.args.get('playback', None)))
        except ValueError:
            return json.dumps({
                    'error': True,
                    'error_type': 'ValueError',
                    'message': 'playback must be an integer greater than 0.'
                })

    if request.args.get('position', None):
        try:
            position = abs(int(request.args.get('position', None)))
        except ValueError:
            return json.dumps({
                    'error': True,
                    'error_type': 'ValueError',
                    'message': 'position must be an integer greater than 0.'
                })

    r_conn.set(election_key + '_PLAYBACK', str(playback))

    if request.args.get('ratelimited', None) or request.args.get('errormode', None):
        return json.dumps({"success": True})
    else:
        if ratelimited:
            return make_response((RATELIMITED_STRING, 403, settings.RATELIMITED_HEADERS))

        if errormode:
            return make_response(json.dumps({"status": 500, "error": True}), 500, settings.ERRORMODE_HEADERS)

    if position + playback < (len(hopper) - 1):
        """
        Needs the if statement here to set the position truly to zero if it's specified
        in the url params.
        """
        if request.args.get('position', None) or request.args.get('playback', None) or request.args.get('ratelimited', None) or request.args.get('errormode', None):
            r_conn.set(election_key + '_POSITION', str(position))
        else:
            r_conn.set(election_key + '_POSITION', str(position + playback))

    else:
        r_conn.set(election_key + '_POSITION', str(len(hopper)))

    recording = hopper[position - 1]

    payload = recording[1].download_as_string()

    return payload

if __name__ == '__main__':
    app.run(host=settings.HOST, port=settings.PUB_PORT, debug=settings.DEBUG)