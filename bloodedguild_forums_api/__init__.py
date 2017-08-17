from bloodedguild_forums_api.api import app
from flask_restful import Resource
from bloodedguild_forums_api.api import api
from bloodedguild_forums_api.db import DatabaseConnector
from bloodedguild_forums_api.jwt_util import (
    JWTConstructor,
    AuthRefresh
)
from flask_jwt import jwt_required, current_identity
from bloodedguild_forums_api.config import config

database_settings = {
    "dbname": config.get("db_name"),
    "user": config.get("username")
}

host = config.get("host")
password = config.get("password")

if host:
    database_settings["host"] = host

if password:
    database_settings["password"] = password

DatabaseConnector.add_settings(database_settings)

jwt_object = JWTConstructor(app, config["secret"])
jwt = jwt_object.create_jwt()
response_handler = jwt_object.get_response_handler()
@jwt.auth_response_handler
def jwt_response_handler(access_token, identity):
    return response_handler(access_token, identity)

AuthRefresh.jwt = jwt

api.add_resource(
    AuthRefresh,
    '/auth/refresh'
)


