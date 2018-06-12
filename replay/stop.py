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

    out,err = utils.stop_recording(racedate)

    if err:
        print(err.decode("utf-8").replace('\n',''))
    else:
        print("[PM2][INFO] Process record-ap-%s stopped" % racedate)