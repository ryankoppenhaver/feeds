from flask import Flask, Response, abort, redirect, render_template, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from pymongo.cursor import Cursor
import pymongo
import json
import os
import hmac
import datetime
import time

app = Flask('feeds')
app.config.update({
    'MONGO_URI': 'mongodb://localhost:27017/feeds',
    'SECRET_KEY': os.urandom(16).hex(),
})
if 'FLASK_SETTINGS' in os.environ:
    app.config.from_envvar('FLASK_SETTINGS')
mongo = PyMongo(app)

from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired

class ExampleForm(FlaskForm):
    text = StringField('text', validators=[DataRequired()])

def require_auth():
    if not hmac.compare_digest(request.form['key'], app.config[SECRET_KEY]):
        abort(403)

def json_unknown(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, Cursor):
        return list(obj)
    elif isinstance(obj, datetime.datetime):
        return time.mktime(obj.timetuple())

@app.route('/')
def slash():
    obj = {'text': '', 'votes': 0}
    vote_obj = mongo.db.votes.find_one({'post_id': 1})
    if vote_obj: obj = vote_obj
    form = ExampleForm()
    form.text.data = obj['text']
    return render_template('index.html', obj=obj, form=form)

@app.route('/feeds')
def feed_index():
    feeds = mongo.db.feeds.find()
    return render_template('feed_index.html', feeds=feeds)

def _get_feed(feed_id):
    mongo.db.feeds.find_one_or_404({'_id': feed_id})
    return mongo.db.calls.find(
        {'feed_id': feed_id},
        projection=['ts','transcriptions'],
        limit=200,
        sort=[('ts', pymongo.DESCENDING)]
    )

@app.route('/feeds/<ObjectId:feed_id>')
def get_feed(feed_id):
    calls = _get_feed(feed_id)
    return render_template('feed.html', calls=calls)

@app.route('/api/feeds/<ObjectId:feed_id>', methods=['GET','POST'])
def get_feed_text(feed_id):
    if request.method == 'GET':
        calls = _get_feed(feed_id)
        out = json.dumps(calls, default=json_unknown)
        return Response(out, mimetype='text/json')
    elif request.method == 'POST':
        require_auth()

        feed = mongo.db.feeds.find_one_or_404({'_id': feed_id})
        #mongod.db.calls.insertMany( TKTK )

        # TODO
        return 'ok'

@app.route('/upvote', methods=['POST'])
def upvote():
    form = ExampleForm()
    if form.validate_on_submit():
        mongo.db.votes.find_one_and_update({'post_id': 1},
                                           {'$inc': {'votes': 1}, '$set': {'text': form.text.data}}, new=True, upsert=True)
    return redirect('/', code=302)

@app.route('/downvote', methods=['POST'])
def downvote():
    form = ExampleForm()
    if form.validate_on_submit():
        mongo.db.votes.find_one_and_update({'post_id': 1},
                                           {'$inc': {'votes': 1}, '$set': {'text': form.text.data}}, new=True, upsert=True)
    return redirect('/', code=302)

if __name__ == '__main__':
    app.run(port=5005, debug=True)
