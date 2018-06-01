import os

from google.cloud import storage

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

def get_recordings(bucket):
    return [b for b in bucket.list_blobs(prefix="apps/%s" % BASE_DIR)]

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)