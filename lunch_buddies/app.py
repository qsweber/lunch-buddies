import logging

from flask import Flask, jsonify, request

# from lunch_buddies.actions import poll_users

app = Flask(__name__)
logger = logging.getLogger(__name__)


@app.route('/api/v0/poll', methods=['POST', 'GET'])
def index():
    logger.info('in here')
    logger.info(request.get_json())

    response = jsonify({
        'foo': 2,
        'bar': 2,
    })

    response.headers.add('Access-Control-Allow-Origin', '*')

    return response
