import psycopg2
from datetime import timedelta
from functools import wraps
from flask import Flask, jsonify, request, make_response, current_app
from flask_restful import Resource
from flask_jwt import (
    JWT,
    current_identity,
    jwt_required,
    _jwt_required,
    JWTError
)
from bloodedguild_forums_api.db import (
    DatabaseAuth,
    DatabaseConnector
)

class AuthRefresh(Resource):
    jwt = None
    method_decorators = [jwt_required()]
    def get(self):
        token = self.jwt.jwt_encode_callback(current_identity)
        return {
            'username': current_identity.username,
            'id': current_identity.id,
            'group': current_identity.group,
            'privilege': current_identity.privilege,
            'access_token': token.decode('utf-8')
        }

class User(object):
    def __init__(self, id, username, group, privilege):
        self.id = id
        self.username = username
        self.group = group
        self.privilege = privilege

class JWTConstructor():
    def __init__(self, app, secret_key):
        app.config['SECRET_KEY'] = secret_key
        app.config['JWT_EXPIRATION_DELTA'] = timedelta(weeks=1)
        self.app = app

    def create_jwt(self):
        return JWT(self.app, self.authenticate, self.identity)

    def authenticate(self, username, password):
        auth_db = DatabaseAuth()
        check_auth = auth_db.check_auth(username, password)
        if check_auth:
            return User(
                check_auth[0],
                check_auth[1],
                check_auth[2],
                check_auth[3]
            )

    def identity(self, payload):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select id, username, name, privilege "
        sql_string += "from users_post_counts "
        sql_string += "where id = %s"
        psql_cursor.execute(
            sql_string,
            (payload["identity"],)
        )
        user_data = psql_cursor.fetchone()
        psql_cursor.close()
        db.close()
        return User(
            user_data[0],
            user_data[1],
            user_data[2],
            user_data[3]
        )

    def get_response_handler(self):
        def jwt_response_handler(access_token, identity):
            return jsonify(
                {
                    'access_token': access_token.decode('utf-8'),
                    'username': identity.username,
                    'id': identity.id,
                    'group': identity.group,
                    'privilege': identity.privilege
                }
            )
        return jwt_response_handler

def jwt_optional(realm=None):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            try:
                _jwt_required(realm or current_app.config['JWT_DEFAULT_REALM'])
            except JWTError:
                pass
            return fn(*args, **kwargs)
        return decorator
    return wrapper
