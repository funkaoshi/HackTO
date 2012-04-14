import sqlite3
from flask import abort, g, flash, make_response, redirect, request, render_template, url_for, Flask
import soundcloud



# configuration

DATABASE = 'jokes.db'
SECRET_KEY = 'Y\xf6\xf2j\xc9\xc5\xbc\xde{\xae\x9a\xc8\x8dZ0\x9e\x14\xb6\x90\xd7\x02\x03\xf0\x1a'
DEBUG = True
SOUNDCLOUD_ID = '790496b735a696eb3261822846618016'
SOUND_CLOUD_SECRET = '838cb0dd9b5bcb39b4036ae222a1c124'


# create application

app = Flask(__name__)
app.config.from_object(__name__)
sc_client = soundcloud.Client(client_id=SOUNDCLOUD_ID)


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


# The Application

@app.route('/')
def index():
    """
    Returns a list of jokes.
    """
    jokes = query_db('SELECT * FROM jokes ORDER BY rank')
    return render_template("index.html", jokes=jokes)


#Twilio stuff
@app.route('/twilio/voice', methods=['GET', 'POST'])
def twilio_voice():
    track = sc_client.get('/resolve', url='http://soundcloud.com/jokeline/untitled-recording')
    url = track.download_url + '?client_id=' + SOUNDCLOUD_ID
    resp = make_response(render_template("twilio/voice.xml", joke_url=url))
    resp.headers['Content-Type'] = 'text/xml'
    return resp


@app.route('/jokes/', methods=['GET'])
def list_jokes():
    jokes = query_db('SELECT * FROM jokes ORDER BY rank')
    return render_template("jokes.xml", jokes=jokes)


@app.route('/jokes/random', methods=['GET']):
def random_joke():
    joke = query_db('SELECT * FROM jokes ORDER BY RANDOM() LIMIT 1;', one=True)
    return render_template("joke.xml", joke=joke)


@app.route('/jokes/<int:joke_id>', methods=['GET']):
def get_joke():
    joke = query_db('SELECT * FROM jokes WHERE id = ? LIMIT 1;', [joke_id], one=True)
    return render_template("joke.xml", joke=joke)


app.route('/jokes/<int:joke_id>', methods=['POST']):
def create_joke():
    # Pull data out of XML request.
    # Create a new joke.
    return render_template("joke.xml", joke=joke)


app.route('/jokes/<int:joke_id>', methods=['PUT']):
def update_joke():
    # Pull data out of request XML.
    # Lookup joke.
    # Update rank of the joke (up or down)
    return render_template("joke.xml", joke=joke)


if __name__ == '__main__':
    app.run("0.0.0.0")
