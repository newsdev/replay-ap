import argparse

from replay import utils


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--racedate', '-r', dest='racedate')
    args = parser.parse_args()
    
    if not args.racedate:
        raise ValueError("You must pass in a racedate if one cannot be found in the final results filename.")
    else:
        racedate = args.racedate

    active, err = utils.get_active_recordings()
    matching_active_recordings = []
    for a in active:
        if "record-ap-%s" % racedate == a['name']:
            have_active_recording = True
            matching_active_recordings.append(a['name'])

    if len(matching_active_recordings) > 0:
        for r in matching_active_recordings:
            # already running
            message = "[PM2][ERROR] Process %s already running" % r)
    else:
        out, err = utils.start_recording(racedate)
        if err:
            # error starting the recording
            message = err.decode('utf-8').replace('\n')
        else:
            # success!
            message = "[PM2][INFO] Process replay-ap-%s started" % racedate
            
            
    print(message)