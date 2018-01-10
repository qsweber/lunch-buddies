from flask import Flask, jsonify

# from lunch_buddies.actions import poll_users

app = Flask(__name__)


@app.route('/api/v0/poll', methods=['POST', 'GET'])
def index():
    response = jsonify({
        'foo': 2,
        'bar': 2,
    })
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response
