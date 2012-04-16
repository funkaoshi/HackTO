from celery.task import task
import os
import requests
import redis
import soundcloud
import sqlite3
import tempfile

from flask import g, make_response, redirect, request, render_template, url_for, Flask


# create application

app = Flask(__name__)
app.config.from_object('settings')

sc_client = soundcloud.Client(client_id=app.config['SOUNDCLOUD_ID'],
                              client_secret=app.config['SOUNDCLOUD_SECRET'],
                              username=app.config['SOUNDCLOUD_USERNAME'],
                              password=app.config['SOUNDCLOUD_PASSWORD'])


r = redis.StrictRedis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], db=app.config['REDIS_DB']) 
# Helpers

def get_sc(sc_id):
    return sc_client.get('/tracks/%s' % sc_id)

def get_sc_url(track):
    return track.stream_url + '?client_id=' + app.config['SOUNDCLOUD_ID']

def get_random_joke():
    return get_sc(r.srandmember('tracks'))
    

def make_xml_response(template, **context):
    response = make_response(render_template(template, **context))
    response.headers['Content-Type'] = 'text/xml'
    return response

@task(name='jokeline.save_recording', ignore_result=True)
def save_recording(joke_url):
    """
    Pulls the recording from Twillio down into a random file, and then uploads
    it to Soundcloud. Once this is complete we store a new entry in our
    database of jokes.
    """
    # TODO: We should be catching exceptions and cleaning up the tempfiles.
    logger = save_recording.get_logger()
    logger.info("Downloading %s" % joke_url)
    j = requests.get(joke_url)
    fh, filename = tempfile.mkstemp()
    f = open(filename, 'w')
    f.write(j.raw.read())
    f.close()
    track = sc_client.post('/tracks', track={
            'title': 'joke',
            'sharing': 'public',
            'asset_data': open(filename, 'rb')
            })
    logger.info("Saved joke to Soundcloud as Track %d" % track.id)
    os.remove(filename)
    r.sadd('tracks', track_id)

# The Web Application

@app.route('/')
def index():
    """
    Returns a random joke to be displayed on the jokeline homepage.
    """
    return render_template("index.html", joke=get_random_joke())


# Endpoints for Twilio.

@app.route('/jokes/random', methods=['GET'])
def random_joke():
    """
    Returns a random joke to the caller.
    """
    return make_xml_response("joke.xml", joke_url=get_sc_url(get_random_joke()))

@app.route('/jokes', methods=['POST'])
def jokes():
    """
    After listing to a joke the user can record their own (or hangup).
    """
    if request.form['Digits'] == '1':
        # User wants to record
        return make_xml_response("record.xml")
    else:
        # User is done with the phone call.
        return make_xml_response("done.xml")

@app.route('/jokes/record', methods=['POST'])
def record_joke():
    """
    Save the recorded joke and hangup.
    """
    save_recording.delay(request.form['RecordingUrl'])
    return make_xml_response("done.xml")

@app.route('/jokes/<int:joke_id>', methods=['PUT'])
def update_joke():
    """
    Users can (eventually) like or dislike a joke.
    """
    # Pull data out of request XML.
    # Lookup joke.
    # Update rank of the joke (up or down)
    return render_template("joke.xml", joke=joke)


if __name__ == '__main__':
    app.run("0.0.0.0")
