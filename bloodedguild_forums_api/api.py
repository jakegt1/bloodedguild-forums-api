from flask import Flask, jsonify, request, make_response
from flask_jwt import JWT, jwt_required, current_identity
from flask_restful import Resource, Api, abort
from datetime import datetime
import sqlite3 as sql
import re
import sys
import hashlib
import psycopg2
from psycopg2.extras import DictCursor
from .config import config;

DB_NAME = config["db_name"]
USER = config["username"]
PASSWORD = config["password"]

class User(object):
    def __init__(self, id, username):
        self.id = id
        self.username = username

def authenticate(username, password):
    auth_db = DatabaseAuth()
    check_auth = auth_db.check_auth(username, password)
    if check_auth:
        return User(check_auth[0], check_auth[3])

def identity(payload):
    db = DatabaseConnector()
    psql_cursor = db.get_cursor()
    sql_string = "select id, username from users "
    sql_string += "where id = %s"
    psql_cursor.execute(
        sql_string,
        (payload["identity"],)
    )
    user_data = psql_cursor.fetchone()

    print(user_data)
    return User(user_data[0], user_data[1])

app = Flask(__name__)
app.config['SECRET_KEY'] = config["secret"]
api = Api(app)

jwt = JWT(app, authenticate, identity)

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
        self.open()

    def get_conn_string(self):
        return str(self.db_string_constructor)

    def get_cursor(self):
        return self.connection.cursor()

    def close(self):
        self.connection.commit()
        self.connection.close()

    def open(self):
        self.connection = psycopg2.connect(
            self.get_conn_string(),
            cursor_factory=DictCursor
        )

class DatabaseAuth():
    def __init__(self):
        self.db = DatabaseConnector()

    def check_auth(self, username, password):
        psql_cursor = self.db.get_cursor()
        sql_string = "select * from users "
        sql_string += "where username = %s"
        sql_string += "and password_hash = crypt(%s, password_hash);"
        psql_cursor.execute(
            sql_string,
            (username, password)
        )
        query_result = psql_cursor.fetchone()
        psql_cursor.close()
        self.db.close()
        return query_result


class DefaultLocation(Resource):
    def get(self):
        return {'info': 'Bloodedguild forums api. Do not touch! wow!'}


class ForumsCategoriesInfo(Resource):
    def construct_subquery_response(self, sql_query):
        return {
            'type': 'subcategory',
            'id': sql_query[0],
            'title': sql_query[1],
            'description': sql_query[2]
        }

    def construct_response(self, sql_query):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select * from subcategories "
        sql_string += "where category_id = %s;"
        psql_cursor.execute(
            sql_string,
            (sql_query[0],)
        )
        forum_subcategories = psql_cursor.fetchall()
        forum_subcategories = [
            self.construct_subquery_response(subcategory)
            for subcategory in
            forum_subcategories
        ]
        psql_cursor.close()
        db.close()
        return {
                'type': 'category',
                'id': sql_query[0],
                'title': sql_query[1],
                'description': sql_query[2],
                'subcategories': forum_subcategories
        }

    def get(self):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select * from categories;"
        psql_cursor.execute(
            sql_string
        )
        forum_categories = psql_cursor.fetchall()
        psql_cursor.close()
        db.close()
        response = []
        if(forum_categories):
            response = [
                self.construct_response(category)
                for category in
                forum_categories
            ]
        return response

class ForumsSubcategoriesInfo(Resource):
    def get(self, category_id):
        return {'type': 'category'}


class ForumsSpecificSubcategoryInfo(Resource):
    def get(self, category_id, subcategory_id):
        return {'type': 'subcategory'}


class ForumsSubcategoryThreads(Resource):
    def construct_response(self, sql_query):
        return {
                'type': 'thread',
                'id': sql_query[0],
                'title': sql_query[1],
                'timestamp': sql_query[2].isoformat(),
                'locked': sql_query[3],
                'user_id': sql_query[6]
        }

    def get_thread(self, category_id, subcategory_id, thread_id):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        offset = int(thread_id)-1 #0 indexed
        sql_string = "select * from threads "
        sql_string += "where category_id = %s and "
        sql_string += "subcategory_id = %s "
        sql_string += "limit 1 "
        sql_string += "offset %s;"
        psql_cursor.execute(
            sql_string,
            (category_id, subcategory_id, offset)
        )
        forum_post = psql_cursor.fetchone()
        psql_cursor.close()
        db.close()
        if(not forum_post):
            forum_post = []
        else:
            forum_post = [self.construct_response(forum_post)]
        return forum_post

    def get_threads(self, category_id, subcategory_id, thread_min, thread_max):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select * from threads "
        sql_string += "where category_id = %s and "
        sql_string += "subcategory_id = %s "
        sql_string += "limit %s "
        sql_string += "offset %s;"
        limit = thread_max-thread_min
        offset = thread_min-1 #0 indexed
        psql_cursor.execute(
            sql_string,
            (
                category_id,
                subcategory_id,
                limit,
                offset
            )
        )
        forum_threads = psql_cursor.fetchall()
        psql_cursor.close()
        db.close()
        return [self.construct_response(thread) for thread in forum_threads]

    def get(self, category_id, subcategory_id, thread_id):
        regex_post = re.compile(r'^\d+$')
        regex_posts = re.compile(r'^(?P<min>\d+)-(?P<max>\d+)$')
        response = {}
        if(regex_post.match(thread_id)):
            response = self.get_thread(
                category_id,
                subcategory_id,
                thread_id
            )
        elif(regex_posts.match(thread_id)):
            matches = regex_posts.match(thread_id)
            min = int(matches.group('min'))
            max = int(matches.group('max'))
            if(min < max and min != 0):
                response = self.get_threads(
                    category_id,
                    subcategory_id,
                    min,
                    max
                )
            else:
                error_message = "Minimum ID given was larger than Maximum ID."
                abort(401, message={"error": error_message})
        else:
            abort(401, message={"error": "thread id did not match regex"})
        return response


class ForumsInfo(Resource):
    def get(self):
        return {
            'type': 'forums',
        }

class ForumsAddThread(ValidatorResource):
    method_decorators = [jwt_required()]
    def put(self, category_id, subcategory_id):
        json_data = self.validate_json(request.get_json())
        db = DatabaseConnector()
        sql_string = "insert into threads "
        sql_string += "("
        sql_string += "title, "
        sql_string += "subcategory_id, "
        sql_string += "category_id, "
        sql_string += "user_id"
        sql_string += ") "
        sql_string += "VALUES (%s, %s, %s, %s) RETURNING id;"
        psql_cursor = db.get_cursor()
        try:
            psql_cursor.execute(
                sql_string,
                (
                    json_data["title"],
                    subcategory_id,
                    category_id,
                    current_identity.id
                )
            )
        except psycopg2.IntegrityError:
            abort(401, message="Error: Database failed to execute insert.")
        new_id = psql_cursor.fetchone()[0]
        psql_cursor.close()
        db.close()
        return {
            'type': 'thread',
            'title': json_data["title"],
            'id': new_id,
            'status': 'created'
        }


class ForumsThread(ValidatorResource):
    def construct_response(self, sql_query):
        return {
                'type': 'post',
                'id': sql_query[0],
                'title': sql_query[1],
                'timestamp': sql_query[2].isoformat(),
                'locked': sql_query[3],
                'user_id': sql_query[6]
        }

    def get(self, thread_id):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select * from threads "
        sql_string += "where id = %s;"
        psql_cursor.execute(
            sql_string,
            (thread_id,)
        )
        forum_thread = psql_cursor.fetchone()
        psql_cursor.close()
        db.close()
        response = []
        if(forum_thread):
            response = [self.construct_response(forum_thread)]
        return response


class ForumsAddPost(ValidatorResource):
    method_decorators = [jwt_required()]
    def put(self, thread_id):
        json_data = self.validate_json(request.get_json())
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select COUNT(*) from posts "
        sql_string += "WHERE thread_id=%s;"
        psql_cursor.execute(
            sql_string,
            (thread_id,)
        )
        post_id = psql_cursor.fetchone()[0] + 1
        sql_string = "insert into posts "
        sql_string += "("
        sql_string += "id, "
        sql_string += "content, "
        sql_string += "thread_id, "
        sql_string += "user_id"
        sql_string += ") "
        sql_string += "VALUES (%s, %s, %s, %s) RETURNING id;"
        try:
            psql_cursor.execute(
                sql_string,
                (
                    post_id,
                    json_data["content"],
                    thread_id,
                    current_identity.id
                )
            )
        except psycopg2.IntegrityError:
            abort(401, message="Error: Database failed to execute insert.")
        new_id = psql_cursor.fetchone()[0]
        psql_cursor.close()
        db.close()
        return {
            'thread': thread_id,
            'type': 'post',
            'id': new_id,
            'status': 'created'
        }


class ForumsPost(Resource):
    def construct_response(self, sql_query):
        return {
                'type': 'post',
                'id': sql_query[0],
                'content': sql_query[1],
                'timestamp': sql_query[2].isoformat(),
                'user_id': sql_query[4]
        }

    def get_post(self, thread_id, post_id):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select * from posts "
        sql_string += "where id=%s and thread_id = %s;"
        psql_cursor.execute(
            sql_string,
            (post_id, thread_id)
        )
        forum_post = psql_cursor.fetchone()
        psql_cursor.close()
        db.close()
        if(not forum_post):
            forum_post = []
        else:
            forum_post = [self.construct_response(forum_post)]
        return forum_post

    def get_posts(self, thread_id, post_min, post_max):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select * from posts "
        sql_string += "where thread_id = %s and "
        sql_string += "id >= %s and "
        sql_string += "id <= %s;"
        psql_cursor.execute(
            sql_string,
            (
                thread_id,
                post_min,
                post_max
            )
        )
        forum_posts = psql_cursor.fetchall()
        psql_cursor.close()
        db.close()
        return [self.construct_response(post) for post in forum_posts]


    def get(self, thread_id, post_id):
        regex_post = re.compile(r'^\d+$')
        regex_posts = re.compile(r'^(?P<min>\d+)-(?P<max>\d+)$')
        response = {}
        if(regex_post.match(post_id)):
            response = self.get_post(thread_id, post_id)
        elif(regex_posts.match(post_id)):
            matches = regex_posts.match(post_id)
            min = int(matches.group('min'))
            max = int(matches.group('max'))
            if(min < max):
                response = self.get_posts(
                    thread_id,
                    min,
                    max
                )
            else:
                error_message = "Minimum ID given was larger than Maximum ID."
                abort(401, message={"error": error_message})
        else:
            abort(401, message={"error": "post id did not match regex"})
        return response

@jwt.auth_response_handler
def jwt_response_handler(access_token, identity):
    return jsonify(
        {
            'access_token': access_token.decode('utf-8'),
            'username': identity.username
        }
    )


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

api.add_resource(DefaultLocation, '/')
forums_required_fields = ([["title"]])
threads_required_fields = ([["content"]])
api.add_resource(
    ForumsCategoriesInfo,
    '/forums/categories'
)
api.add_resource(
    ForumsSubcategoriesInfo,
    '/forums/categories/<int:category_id>'
)
api.add_resource(
    ForumsSpecificSubcategoryInfo,
    '/forums/categories/<int:category_id>/<int:subcategory_id>'
)
api.add_resource(
    ForumsSubcategoryThreads,
    '/forums/categories/<int:category_id>/<int:subcategory_id>/<string:thread_id>'
)
api.add_resource(
    ForumsAddThread,
    '/forums/categories/<int:category_id>/<int:subcategory_id>',
    resource_class_args=forums_required_fields
)
api.add_resource(ForumsInfo,'/forums')
api.add_resource(ForumsThread, '/forums/threads/<int:thread_id>')
api.add_resource(
    ForumsAddPost,
    '/forums/threads/<int:thread_id>',
    resource_class_args=threads_required_fields
)
api.add_resource(
    ForumsPost,
    '/forums/threads/<int:thread_id>/<string:post_id>'
)

if __name__ == '__main__':
    app.run(debug=True)
