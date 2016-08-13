from flask import Flask, jsonify, request, make_response, abort
from flask.ext.httpauth import HTTPBasicAuth
from flask_restful import Resource, Api
import sqlite3 as sql
import sys
import hashlib

auth = HTTPBasicAuth()
app = Flask(__name__)
api = Api(app)

class DefaultLocation(Resource):
    def get(self):
        return {'info': 'Bloodedguild forums api. Do not touch! wow!'}

api.add_resource(DefaultLocation, '/')

if __name__ == '__main__':
    app.run(debug=True)
