import datetime
import json
import os
import subprocess

from google.cloud import storage
from google.oauth2 import service_account
import googleapiclient.discovery


BASE_DIR = os.environ.get('REPLAY_AP_BASE_DIR', 'replay-ap/')

def build_context():
    """
    Every page needs these two things.
    """
    context = {}
    return dict(context)

def to_bool(v):
    if not v:
        return False
    return v.lower() in (b"yes", b"true", b"t", b"1")

def get_bucket():
    client = storage.Client()
    return client.get_bucket(os.environ.get('REPLAY_AP_BUCKET', 'int.nyt.com'))

def get_completed_recordings(bucket):
    return [b for b in bucket.list_blobs(prefix="apps/%s" % BASE_DIR) if "__placeholder__" not in b.public_url]

def get_racedates(bucket):
    recordings = [b for b in bucket.list_blobs(prefix="apps/%s" % BASE_DIR) if "__placeholder__" in b.public_url]
    return sorted(list(set([b.public_url.split(BASE_DIR)[1].split('/national')[0].replace('/', '') for b in recordings])), key=lambda x:x)

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
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    SERVICE_ACCOUNT_FILE = os.environ.get('REPLAY_AP_CREDS', 'credentials.json')
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = googleapiclient.discovery.build('sheets', 'v4', credentials=credentials)
    SHEETID = os.environ.get('REPLAY_AP_CALENDAR_SHEETID', '')
    RANGE = os.environ.get('REPLAY_AP_CALENDAR_RANGE', '')
    result = service\
                .spreadsheets()\
                .values()\
                .get(spreadsheetId=SHEETID,range=RANGE)\
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