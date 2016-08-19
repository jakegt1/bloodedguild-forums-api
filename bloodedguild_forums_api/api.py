from flask import Flask, jsonify, request, make_response
from flask_restful import Resource, Api, abort
import sqlite3 as sql
import sys
import hashlib
import psycopg2
from config import config;

DB_NAME = config["db_name"]
USER = config["username"]
PASSWORD = config["password"]

app = Flask(__name__)
api = Api(app)

class ValidatorResource(Resource):
    def __init__(self, required_fields=[]):
        super().__init__()
        self.required_fields = required_fields

    def validate_json(self, json_data):
        missing_fields = []
        for field in self.required_fields:
            if(field not in json_data.keys()):
                missing_fields.append(field)
        if(missing_fields):
            error_string = "The JSON data was missing the following fields:"
            for field in missing_fields:
                error_string += field+","
                error_string = error_string[:-1] #trim last comma
                abort(400, message=error_string)
        else:
            return json_data

class DatabaseStringConstructor():
    def __init__(self, db_name, user, password):
        self.db_name = db_name
        self.user = user
        self.password = password

    def __str__(self):
        conn_string = "host='localhost' "
        conn_string +="dbname='"+self.db_name+"' "
        conn_string +="user='"+self.user+"' "
        conn_string +="password='"+self.password+"' "
        return conn_string


class DatabaseConnector():
    def __init__(self):
        self.db_string_constructor = DatabaseStringConstructor(
            DB_NAME,
            USER,
            PASSWORD
        )

    def get_conn_string(self):
        return str(db_string_constructor)

    def make_connection(self):
        connection = psycopg2.connect(self.get_conn_string())
        return connection.cursor()


class DefaultLocation(Resource):
    def get(self):
        return {'info': 'Bloodedguild forums api. Do not touch! wow!'}


class Forums(ValidatorResource):

    def get(self):
        return {
            'type': 'forums',
        }

    def put(self):
        json_data = self.validate_json(request.get_json())
        return {
            'title': json_data["title"],
            'type': 'thread',
            'id': 'SOME/FUCKING/ID',
            'status': 'created'
        }


class ForumsThread(ValidatorResource):
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

class ForumsPost(ValidatorResource):
    def get(self, thread_id, post_id):
        return {
            'type': 'post',
            'id': post_id,
            'thread_id': thread_id
        }

api.add_resource(DefaultLocation, '/')
forums_required_fields = ([["title","category_id", "subcategory_id"]])
api.add_resource(
    Forums,
    '/forums',
    resource_class_args=forums_required_fields
)
api.add_resource(ForumsThread, '/forums/<int:thread_id>')
api.add_resource(ForumsPost, '/forums/<int:thread_id>/<int:post_id>')

if __name__ == '__main__':
    app.run(debug=True)
