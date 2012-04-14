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
    placeholders = ', '.join(['?' for i in range(len(values))])
    query = "INSERT INTO %s (%s) VALUES (%s)" % (table, columns, placeholders)
    g.db.execute(query, values)
    g.db.commit()


# The Application

@app.route('/')
def index():
    """
    Returns a list of jokes.
    """
    jokes = query_db('SELECT * FROM jokes ORDER BY rank')
    return render_template("index.html", jokes=jokes)


#Twilio stuff

def get_sc_url(sc_id):
    track = sc_client.get('/tracks/%d' % sc_id)
    url = track.stream_url + '?client_id=' + app.config['SOUNDCLOUD_ID']
    return url


def make_xml_response(template, **context):
    response = make_response(render_template(template, **context))
    response.headers['Content-Type'] = 'text/xml'
    return response


@app.route('/twilio/voice', methods=['GET', 'POST'])
def twilio_voice():
    """
    A test URL.
    """
    url = get_sc_url(43112949)
    return make_xml_response("twilio/voice.xml", joke_url=url)


@app.route('/jokes', methods=['GET', 'POST'])
def jokes():
    if request.method == 'GET':
        jokes = query_db('SELECT * FROM jokes ORDER BY rank')
        return make_xml_response("jokes.xml", jokes=jokes)
    elif request.method == 'POST':
        # Create a new joke.
        print request.form['Digits']
        if request.form['Digits'] == '1':
            #user wants to record
            return make_xml_response("record.xml")
        else:
            #decline
            return make_xml_response("decline.xml")


@app.route('/jokes/record', methods=['POST'])
def record():
    joke_url = request.form['RecordingUrl']
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
    return make_xml_response("decline.xml")


@app.route('/jokes/random', methods=['GET'])
def random_joke():
    joke = query_db('SELECT * FROM jokes ORDER BY RANDOM() LIMIT 1;', one=True)
    joke['url'] = get_sc_url(joke['track_id'])
    return make_xml_response("joke.xml", joke=joke)


app.route('/jokes/<int:joke_id>', methods=['PUT'])
def update_joke():
    # Pull data out of request XML.
    # Lookup joke.
    # Update rank of the joke (up or down)
    return render_template("joke.xml", joke=joke)


if __name__ == '__main__':
    app.run("0.0.0.0")
