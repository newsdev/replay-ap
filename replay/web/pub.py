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
    return redirect(settings.ADM_URL)

@app.route('/elections/<racedate>')
def replay(racedate):
    national = True
    if request.args.get('national', None):
        if request.args['national'].lower() == 'false':
            national = False
    print("replay pub: national=%s" % national)
    return utils.get_replay_file(racedate, national=national)

if __name__ == '__main__':
    app.run(host=settings.HOST, port=settings.PUB_PORT, debug=settings.DEBUG)