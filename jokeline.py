import sqlite3
import tempfile
from flask import g, make_response, redirect, request, render_template, url_for, Flask
import soundcloud
import requests


# create application

app = Flask(__name__)
app.config.from_object('settings')

sc_client = soundcloud.Client(client_id=app.config['SOUNDCLOUD_ID'],
                              client_secret=app.config['SOUNDCLOUD_SECRET'],
                              username=app.config['SOUNDCLOUD_USERNAME'],
                              password=app.config['SOUNDCLOUD_PASSWORD'])


# Poor Man's 'ORM' with SQLite3

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.close()

def query_db(query, args=(), one=False):
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0], value)
               for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv

def insert_into_db(table, columns, values):
    columns = ', '.join(["'%s'" % column for column in columns])
    placeholders = ', '.join(['?'] * len(columns))
    query = "INSERT INTO %s (%s) VALUES (%s)" % (table, columns, placeholders)
    g.db.execute(query, values)
    g.db.commit()


# Helpers

def get_sc(sc_id):
    return sc_client.get('/tracks/%d' % sc_id)

def get_sc_url(sc_id):
    return get_sc(sc_id).stream_url + '?client_id=' + app.config['SOUNDCLOUD_ID']

def get_random_joke():
    joke = query_db('SELECT * FROM jokes ORDER BY RANDOM() LIMIT 1;', one=True)
    joke['url'] = get_sc_url(joke['track_id'])
    return joke

def make_xml_response(template, **context):
    response = make_response(render_template(template, **context))
    response.headers['Content-Type'] = 'text/xml'
    return response

def save_recording(joke_url):
    """
    Pulls the recording from Twillio down into a random file, and then uploads
    it to Soundcloud. Once this is complete we store a new entry in our
    database of jokes.
    """
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
    insert_into_db('jokes', ['joke', 'track_id', 'rank'], [track.title, track.id, 0])


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
    return make_xml_response("joke.xml", joke=get_random_joke())

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
    # TODO: Do this outside the webapp.
    save_record(request.form['RecordingUrl'])
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
