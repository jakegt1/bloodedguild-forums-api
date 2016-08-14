from flask import Flask, jsonify, request, make_response, abort
from flask_restful import Resource, Api
import sqlite3 as sql
import sys
import hashlib

app = Flask(__name__)
api = Api(app)

class DefaultLocation(Resource):
    def get(self):
        return {'info': 'Bloodedguild forums api. Do not touch! wow!'}


class Forums(Resource):
    def get(self):
        return {
            'type': 'forums',
        }

    def put(self):
        print("create some thread")
        return {
            'type': 'thread',
            'id': 'SOME/FUCKING/ID',
            'status': 'created'
        }


class ForumsThread(Resource):
    def get(self, thread_id):
        return {
            'type': 'thread',
            'id': thread_id,
        }

    def put(self, thread_id):
        return {
            'type': 'post',
            'thread_id': thread_id,
            'status': 'created'
        }

class ForumsPost(Resource):
    def get(self, thread_id, post_id):
        return {
            'type': 'post',
            'id': post_id,
            'thread_id': thread_id
        }

api.add_resource(DefaultLocation, '/')
api.add_resource(Forums, '/forums')
api.add_resource(ForumsThread, '/forums/<int:thread_id>')
api.add_resource(ForumsPost, '/forums/<int:thread_id>/<int:post_id>')

if __name__ == '__main__':
    app.run(debug=True)
