import json
import os

import utils


def generate_racedate_folders():

    racedates = [r['date'] for r in utils.get_calendar()]
    for racedate in racedates:
        print(racedate)
        data_dir = os.environ.get('REPLAY_AP_DATA_DIR', '/tmp')
        os.system('mkdir -p %(data_dir)s/%(racedate)s/national/' % {'data_dir': data_dir, 'racedate': racedate})
        os.system('touch %(data_dir)s/%(racedate)s/national/__placeholder__' % {'data_dir': data_dir, 'racedate': racedate}) 
        os.system('gsutil cp %(data_dir)s/%(racedate)s/national/__placeholder__ gs://%(bucket)s/%(path)s/' % {'data_dir': data_dir, 'racedate': racedate, 'bucket': os.environ.get('REPLAY_AP_BUCKET', 'int.nyt.com'), 'path': os.environ.get('REPLAY_AP_BASE_PATH', 'apps/replay-ap/%s/national' % racedate)})

if __name__ == "__main__":
    generate_racedate_folders()