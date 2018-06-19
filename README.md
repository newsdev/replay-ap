# REPLAY-AP
[That strange feeling we sometimes get that we've lived through something before.](https://www.youtube.com/watch?v=G2eUopy9sd8)

`replay-ap` is a small web service that will record and replay JSON from an AP election test. `replay-ap` persists to Google Cloud Storage and does not require a database.

## User interface
![user_interface](https://user-images.githubusercontent.com/109988/41559986-ba63e4a0-7313-11e8-9200-381512097225.png)

## Getting Started
#### Install requirements

`replay-ap` requires a running redis instance for storing state (this will probably be refactored away in a future release). Install with homebrew (development on a Mac) or via apt-get (production use on an Ubuntu-based server) or use a cloud-based Redis provider like we do.

`replay-ap` also requires Google Cloud Storage. The authentication for that service is beyond the scope of this document. You can see [this guide](https://cloud.google.com/storage/docs/authentication) for more information.

##### Mac
Requires [Homebrew](http://brew.sh/index.html).

```
brew install redis
brew services start redis
```

##### Ubuntu Linux
```
Sudo apt-get install redis-server
```

#### Install this app
```bash
mkvirtualenv replay-ap && git clone git@github.com:newsdev/replay-ap.git && cd replay-ap
pip install -r requirements.txt
add2virtualenv ap_deja_vu
```

#### Run The Servers
In one terminal window, run the admin app.
```bash
workon replay-ap
python replay/web/adm.py
```

In another window, run the public app.
```bash
workon replay-ap
python replay/web/pub.py
```

## How It Works

#### Environment Variables
Minimally, your app needs to export a GCS bucket name and a base path for your files.

If you want your files to be stored at `fake.bucket.nyt.com/apps/replay-ap/`, you would export the following:

```
export STORAGE_BUCKET = fake.bucket.nyt.com 
export BASE_DIR = apps/replay-ap/
```

Files will be written to `$STORAGE_BUCKET/$BASE_DIR/$RACEDATE/national/$RACEDATE-$TIMESTAMP.json`

`$RACEDATE` and `$TIMESTAMP` are created as needed.

#### Playback

The route `/elections/<racedate>` will replay the election files found in
`$STORAGE_BUCKET/$BASE_DIR/$RACEDATE/national/`.

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
files in your `$STORAGE_BUCKET/$BASE_DIR/$RACEDATE/national/` named 001.json through 109.json

* Request 1: `/elections/<racedate>?position=0&playback=10&national=true` > 001.json
* Request 2: `/elections/<racedate>?national=true` > 011.json
* Request 3: `/elections/<racedate>?national=true` > 021.json
* Request 4: `/elections/<racedate>?national=true` > 031.json
* Request 5: `/elections/<racedate>?national=true` > 041.json
* Request 6: `/elections/<racedate>?national=true` > 051.json
* Request 7: `/elections/<racedate>?national=true` > 061.json
* Request 8: `/elections/<racedate>?national=true` > 071.json
* Request 9: `/elections/<racedate>?national=true` > 081.json
* Request 10: `/elections/<racedate>?national=true` > 091.json
* Request 11: `/elections/<racedate>?national=true` > 101.json
* Request 12: `/elections/<racedate>?national=true` > 109.json
* Request 13 - ???: `/elections/<racedate>?national=true` > 109.json

Requesting `/elections/<racedate>?position=0&playback=1&national=true` will reset to the default position
and playback speeds, respectively.

#### Status

The route `/elections/<racedate>/status` will return the status of a given
election date test, including the current position in the hopper, the
playback speed, and the path of the file that will be served at the current
position.

```javascript
    {
        "playback": 1, 
        "position": 28, 
        "errormode": false, 
        "ratelimited": false, 
        "file": "https://storage.googleapis.com/fake.bucket.nyt.com/apps/replay-ap/2018-06-19/national/2018-06-19-1529338461.json", 
        "level": "national"
    }
```
