from bloodedguild_forums_api.api import app
from bloodedguild_forums_api.jwt_constructor import JWT_Constructor
from bloodedguild_forums_api.config import config
jwt_object = JWT_Constructor(app, config["secret"])
jwt = jwt_object.create_jwt()
response_handler = jwt_object.get_response_handler()
@jwt.jwt_response_handler
def jwt_response_handler(access_token, identity):
    return response_handler(access_token, identity)

