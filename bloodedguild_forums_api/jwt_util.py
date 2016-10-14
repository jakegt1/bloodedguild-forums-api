import psycopg2
from datetime import timedelta
from flask import Flask, jsonify, request, make_response
from flask_restful import Resource
from flask_jwt import JWT, current_identity, jwt_required
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
            'access_token': token.decode('utf-8')
        }

class User(object):
    def __init__(self, id, username, group):
        self.id = id
        self.username = username
        self.group = group

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
            return User(check_auth[0], check_auth[1], check_auth[2])

    def identity(self, payload):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select id, username, name from users_post_counts "
        sql_string += "where id = %s"
        psql_cursor.execute(
            sql_string,
            (payload["identity"],)
        )
        user_data = psql_cursor.fetchone()
        psql_cursor.close()
        db.close()
        return User(user_data[0], user_data[1], user_data[2])

    def get_response_handler(self):
        def jwt_response_handler(access_token, identity):
            return jsonify(
                {
                    'access_token': access_token.decode('utf-8'),
                    'username': identity.username,
                    'id': identity.id,
                    'group': identity.group
                }
            )
        return jwt_response_handler


