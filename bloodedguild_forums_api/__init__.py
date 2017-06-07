from bloodedguild_forums_api.api import app
from bloodedguild_forums_api.api import api
from bloodedguild_forums_api.db import (
    DatabaseConnector,
    DatabaseStringConstructor
)
from bloodedguild_forums_api.jwt_util import (
    JWTConstructor,
    AuthRefresh
)
from bloodedguild_forums_api.config import config

DatabaseConnector.db_string_constructor = DatabaseStringConstructor(
    config["db_name"],
    config["username"],
    config["password"]
)

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
