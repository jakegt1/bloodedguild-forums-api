from bloodedguild_forums_api.api import app
from bloodedguild_forums_api.config import config
from bloodedguild_forums_api.jwt import JWT_Constructor
jwt_object = JWT_Constructor(app, config["secret"])
jwt = jwt_object.create_jwt()
response_handler = jwt_object.get_response_handler()
@jwt.auth_response_handler
def jwt_response_handler(access_token, identity):
    return response_handler(access_token, identity)

