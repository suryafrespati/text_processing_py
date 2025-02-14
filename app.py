from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from pathlib import Path  # Python 3.6+ only
import json
import os
import requests
import operator
import re
import nltk
from stop_words import stops
from collections import Counter
from bs4 import BeautifulSoup

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from models import Result
from models import User

@app.route('/', methods=['GET', 'POST'])
def index():
    errors = []
    results = {}
    
    if request.method == 'POST':
        # get url that the user has entered
        try:
            url = request.form['url']
            print('url', url)
            r = requests.get(url)
            print(r.text)
        except:
            errors.append(
                "Unable to get URL. Please make sure it's valid and try again."
            )
            return render_template('index.html', errors=errors)

        if r:
            # text processing
            raw = BeautifulSoup(r.text, 'html.parser').get_text()
            nltk.data.path.append('./nltk_data/')  # set the path
            tokens = nltk.word_tokenize(raw)
            text = nltk.Text(tokens)
            # remove punctuation, count raw words
            nonPunct = re.compile('.*[A-Za-z].*')
            raw_words = [w for w in text if nonPunct.match(w)]
            raw_word_count = Counter(raw_words)
            # stop words
            no_stop_words = [w for w in raw_words if w.lower() not in stops]
            no_stop_words_count = Counter(no_stop_words)
            # save the results
            results = sorted(
                no_stop_words_count.items(),
                key=operator.itemgetter(1),
                reverse=True
            )
            try:
                result = Result(
                    url=url,
                    result_all=raw_word_count,
                    result_no_stop_words=no_stop_words_count
                )
                db.session.add(result)
                db.session.commit()
            except:
                errors.append("Unable to add item to database.")

    return render_template('index.html', errors=errors, results=results)

@app.route('/app-version', methods=['GET'])
def get_app_version():
    status = 'success'
    version = '1.0'
    query = request.args

    return jsonify({
        'status': 'success',
        'data': {
            'version': version,
            'query': query,
        },
    })

@app.route('/users', methods=['GET'])
def get_users():
    limit = request.args.get('limit')

    if limit:
        users = User.query.limit(limit).all()
    else:
        users = User.query.all()
    
    parsed_users = [u.to_dict() for u in users]

    return jsonify({
        'status': 'success',
        'data': parsed_users,
    })

@app.route('/users', methods=['POST'])
def create_user():
    headers = request.headers
    body = request.get_json()

    if not body:
        return jsonify({
            'status': 'failed',
            'data': {},
        })

    user = User(
        body['username'],
        body['email']
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'data': user.id,
    })

if __name__ == '__main__':
    """
    you would need this code to run under python command insttead of flask
    """
    app.run()
