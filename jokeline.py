import sqlite3
from flask import abort, g, flash, redirect, request, render_template, url_for, Flask


# configuration

DATABASE = 'jokes.db'
SECRET_KEY = 'Y\xf6\xf2j\xc9\xc5\xbc\xde{\xae\x9a\xc8\x8dZ0\x9e\x14\xb6\x90\xd7\x02\x03\xf0\x1a'
DEBUG = True


# create application

app = Flask(__name__)
app.config.from_object(__name__)


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
    jokes = query_db('select * from jokes order by rank')
    return render_template("index.html", jokes=jokes)


if __name__ == '__main__':
    app.run("0.0.0.0")
