from flask import request

from api_handlers import users
from app_init import app
from util import POST_REQUEST, ParsedRequest, api_response, json_response


# user registration route
# POST request
@app.route("/users/register/", **POST_REQUEST)
@app.route("/register", **POST_REQUEST)
@api_response
def register():
    return users.register(ParsedRequest())


# refresh the JWT Token
# GET request
@app.route("/u/token/refresh/", strict_slashes=False)
@api_response
def refesh_token():
    return users.re_authenticate(ParsedRequest())


@app.route("/u/discord/auth/code/", **POST_REQUEST)
@api_response
def setup_discord_auth():
    return users.setup_discord(ParsedRequest())


# ===========================================================================
#                                  Users


# Get user info, secure data is removed for unauthenticated
# requests
@app.route("/users/<user>/data/", strict_slashes=False)
@api_response
def user_details(user):
    return users.get_user_details(ParsedRequest(), user)


# edit user info, only authenticated requests allowed
@app.route("/users/<user>/edit/", **POST_REQUEST)
@api_response
def edit_user(user):
    return users.edit(ParsedRequest(), user)


@app.route("/users/login/", **POST_REQUEST)
@api_response
def user_login():
    return users.login(ParsedRequest())


# user leaderboard
@app.route("/users/all/", strict_slashes=False)
@api_response
def all_users():
    return users.user_list()


@app.route("/users/auth/check/", strict_slashes=False)
@api_response
def check_auth_resp():
    return users.check_auth()


@app.route("/logout/", strict_slashes=False)
@api_response
def log_user_out():
    return json_response({}, headers={"x-access-token": "", "x-refresh-token": ""})

