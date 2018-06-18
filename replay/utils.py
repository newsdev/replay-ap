import datetime
import importlib
import json
import os
import subprocess

from flask import Flask, render_template, request, make_response, Response, redirect
from google.cloud import storage
from google.oauth2 import service_account
import googleapiclient.discovery

settings = importlib.import_module('config.%s.settings' % os.environ.get('DEPLOYMENT_ENVIRONMENT', 'dev'))

r_conn = settings.REDIS_CONNECTION

def build_context():
    """
    Every page needs these two things.
    """
    context = {}
    context['ADM_URL'] = settings.ADM_URL
    context['PUB_URL'] = settings.PUB_URL
    context['STORAGE_BUCKET'] = settings.STORAGE_BUCKET
    return dict(context)

def to_bool(v):
    if not v:
        return False
    return v.lower() in (b"yes", b"true", b"t", b"1")

def get_bucket():
    client = storage.Client()
    return client.get_bucket(settings.STORAGE_BUCKET)

def get_completed_recordings(bucket):
    return [b for b in bucket.list_blobs(prefix="apps/%s" % settings.BASE_DIR) if "__placeholder__" not in b.public_url]

def get_racedates(bucket):
    recordings = [b for b in bucket.list_blobs(prefix="apps/%s" % settings.BASE_DIR) if "__placeholder__" in b.public_url]
    return sorted(list(set([b.public_url.split(settings.BASE_DIR)[1].split('/national')[0].replace('/', '') for b in recordings])), key=lambda x:x)

def stop_recording(racedate):
    process = subprocess.Popen([
        "pm2", "delete",
        "record-ap-%s" % racedate
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out,err = process.communicate()
    return out,err

def start_recording(racedate):
    process = subprocess.Popen([
        "pm2", "start", 
        "replay/record.sh", "--name", "record-ap-%s" % racedate, 
        "--", "%s" % racedate
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out,err = process.communicate()
    return out,err

def get_active_recordings():
    process = subprocess.Popen(['pm2', 'jlist'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out,err = process.communicate()

    try:
        return ([l for l in json.loads(out) if "record-ap" in l['name']], err)
    except:
        pass
    return ([],err)

def get_calendar():
    """
    This is some garbage from the official google docs
    on the Python API but I have zero belief it will
    continue working. Requires a service account and
    the service account must have Viewer permissions
    and be invited as a read-only member of the sheet.
    """
    credentials = service_account.Credentials.from_service_account_file(settings.SERVICE_ACCOUNT_FILE, scopes=settings.SCOPES)
    service = googleapiclient.discovery.build('sheets', 'v4', credentials=credentials)
    result = service\
                .spreadsheets()\
                .values()\
                .get(spreadsheetId=settings.SHEETID,range=settings.RANGE)\
                .execute()
    values = result.get('values', [])

    # values is a list of lists where the headers are the first row.
    # Make sure to narrow your requests to a range where the sheet 
    # actually makes sense as a sheet with headers.
    headers = values[0]

    # This zips the headers and the values for each row together
    # into a dictionary. Probably the fastest way, but :shruggie:
    calendar = [dict(zip(headers,v)) for v in values[1:] if len(v) > 0]

    return calendar

def is_current(racedate):
    """
    Between today and 21 days from today.
    """
    today = datetime.datetime.now()
    future = today + datetime.timedelta(21)
    today = today.strftime('%Y-%m-%d')
    future = future.strftime('%Y-%m-%d')

    racedate = int(racedate.replace('-', ''))
    today = int(today.replace('-', ''))
    future = int(future.replace('-', ''))

    if today <= racedate <= future:
        return True
    return False

def is_future(racedate):
    """
    More than 21 days from today.
    """
    today = datetime.datetime.now()
    future = today + datetime.timedelta(21)
    future = future.strftime('%Y-%m-%d')

    racedate = int(racedate.replace('-', ''))
    future = int(future.replace('-', ''))

    if racedate > future:
        return True
    return False

def is_elec(e, file_path):
    try:
        file_path = file_path.split('/national/')[1]
        if e in file_path:
            return True
    except:
        pass
    return False

def make_ap_response(response_string):
    AP_HEADERS = {
        "cache-control": "private",
        "Connection": "keep-alive",
        "Content-Type": "text/html; charset=utf-8",
        "Date": "Mon, 18 Jun 2018 19:03:47 GMT",
        "etag": "6c67e990bf8e68fd922b047c13776625-20180618162409387-JSON",
        "last-modified": "Mon, 18 Jun 2018 16:24:09 GMT",
        "Server": "Microsoft-IIS/7.5",
        "x-Apigee-CHT": "false",
        "x-apigee-Q-Used": "5/10",
        "x-apigee-Sid": "20180618190347.657Zrmp-xxxxxxxxxxxxx-x-xx",
        "x-aspnet-version": "4.0.30319",
        "x-powered-by": "ASP.NET",
    }
    r = make_response(response_string)
    for k,v in AP_HEADERS.items():
        r.headers[k] = v
    return r

def get_replay_file(racedate):
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

    bucket = get_bucket()
    completed_recordings = get_completed_recordings(bucket)
    if len(completed_recordings) == 0:
        return make_response(json.dumps({"status": 500, "error": True}), 500, settings.ERRORMODE_HEADERS)

    sd = datetime.datetime.now() + datetime.timedelta(0, 60)

    hopper = sorted([(b.public_url, b) for b in completed_recordings if is_elec(racedate, b.public_url.split(settings.BASE_DIR)[1])], key=lambda x:x[0])        

    position = int(r_conn.get(election_key + '_POSITION') or 0)
    playback = int(r_conn.get(election_key + '_PLAYBACK') or 1)

    errormode = to_bool(r_conn.get(election_key + '_ERRORMODE'))
    ratelimited = to_bool(r_conn.get(election_key + '_RATELIMITED'))

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
            return make_ap_response((RATELIMITED_STRING, 403, settings.RATELIMITED_HEADERS))

        if errormode:
            return make_ap_response(json.dumps({"status": 500, "error": True}), 500, settings.ERRORMODE_HEADERS)

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
    r = recording[1].download_as_string() 
    return make_ap_response(r)