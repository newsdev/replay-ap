#!/bin/bash

if [[ ! -z $1 ]] ; then
    RACEDATE=$1
fi

if [[ -z $AP_API_BASE_URL ]] ; then
    AP_API_BASE_URL="http://api.ap.org/v2"
fi

if [[ -z $RACEDATE ]] ; then
    echo 'Provide a race date, such as 2018-11-06'
    exit 1
fi

if [[ -z $REPLAY_AP_BUCKET ]] ; then
    REPLAY_AP_BUCKET="int.nyt.com"
fi

if [[ -z $REPLAY_AP_BASE_PATH ]] ; then
    REPLAY_AP_BASE_PATH="apps/replay-ap/$RACEDATE/national"
fi

if [[ -z $ELEX_LOADER_TIMEOUT ]] ; then
    ELEX_LOADER_TIMEOUT=30
fi

if [[ -z $DATA_DIR ]] ; then
    DATA_DIR="/tmp"
fi

function get_results {
  curl --compressed -f -o $DATA_DIR/$RACEDATE/national/$RACEDATE-$TIMESTAMP.json $AP_API_BASE_URL"/elections/$RACEDATE?apiKey=$AP_API_KEY&format=json&level=ru&test=true"
  gsutil cp $DATA_DIR/$RACEDATE/national/$RACEDATE-$TIMESTAMP.json gs://$REPLAY_AP_BUCKET/$REPLAY_AP_BASE_PATH/
  rm -rf $DATA_DIR/$RACEDATE/national/$RACEDATE-$TIMESTAMP.json
}

for (( i=1; i<100000; i+=1 )); do

  TIMESTAMP=$(date +%s)

  mkdir -p $DATA_DIR/$RACEDATE/national/

  get_results

  sleep $ELEX_LOADER_TIMEOUT

done