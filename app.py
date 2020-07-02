from flask import request

from api_handlers import users, teams, admin, submissions, temp_tokens
from app_init import app
from util import ParsedRequest, api_response, json_response

# Flask config
POST_REQUEST = dict(strict_slashes=False, methods=["post"])

# user registration route
# POST request
@app.route("/users/register/", **POST_REQUEST)
@app.route("/register", **POST_REQUEST)
@api_response
def register():
    return users.register(ParsedRequest(request))


# refresh the JWT Token
# GET request
@app.route("/u/token/refresh/", strict_slashes=False)
@api_response
def refesh_token():
    return users.re_authenticate(ParsedRequest(request))


@app.route("/u/discord/auth/code/", **POST_REQUEST)
@api_response
def sign_discord_token():
    return users.get_discord_token(ParsedRequest(request))


# ===========================================================================
#                                  Users


# Get user info, secure data is removed for unauthenticated
# requests
@app.route("/users/<user>/data/", strict_slashes=False)
@api_response
def user_details(user):
    return users.get_user_details(ParsedRequest(request), user)


# edit user info, only authenticated requests allowed
@app.route("/users/<user>/edit/", **POST_REQUEST)
@api_response
def edit_user(user):
    return users.edit(ParsedRequest(request), user)


@app.route("/users/login/", **POST_REQUEST)
@api_response
def user_login():
    return users.login(ParsedRequest(request))


# user leaderboard
@app.route("/users/all/", strict_slashes=False)
@api_response
def all_users():
    return users.user_list()


# clan leaderabord
@app.route("/clans/all/", strict_slashes=False)
@api_response
def all_teams():
    return teams.team_list()


# ===========================================================================
# ===========================================================================
#                            Teams

# create clan for a particular event
@app.route("/<event>/clans/create/", **POST_REQUEST)
@api_response
def create_team(event):
    return teams.create_team(ParsedRequest(request), event)


# view clan info
@app.route("/clans/<clan>/data/", strict_slashes=False)
@api_response
def get_team(clan):
    return teams.get_team(ParsedRequest(request), clan)


# invite a member or accept an invite
@app.route("/clans/<clan>/members/invite/", **POST_REQUEST)
@app.route("/clans/<clan>/members/add/", **POST_REQUEST)
@api_response
def add_member(clan):
    return teams.add_member(ParsedRequest(request), clan)


# reject a member's request to join the clan
# or remove existing member from clan
@app.route("/clans/<clan>/members/reject/", **POST_REQUEST)
@app.route("/clans/<clan>/members/remove/", **POST_REQUEST)
@api_response
def remove_member(clan):
    return teams.remove_member(ParsedRequest(request), clan)


# request to join a clan
# or join a clan that has invited you
@app.route("/<event>/clans/<clan>/request/", strict_slashes=False)
@app.route("/<event>/clans/<clan>/join/", strict_slashes=False)
@api_response
def request_to_join(event, clan):
    return teams.request_to_join(ParsedRequest(request), clan, event)


@app.route("/<event>/clans/<clan>/submi/", **POST_REQUEST)
@api_response
def submit_proj(event, clan):
    return submissions.submit(ParsedRequest(request), event, clan)


# register for a gaming event
@app.route("/g/gaming/<game>/register/", **POST_REQUEST)
@api_response
def register_game(game):
    return teams.register_for_game(ParsedRequest(request), game)


# ===========================================================================
# ===========================================================================
#                                  Admin

# rate a submission
@app.route("/admin/<team>/score/", **POST_REQUEST)
@api_response
def admin_score(team):
    return admin.score_team(ParsedRequest(request), team)


@app.route("/admin/<team>/disqualify/", **POST_REQUEST)
@api_response
def admin_disqualify(team):
    return admin.disqualify(ParsedRequest(team), team)


@app.route("/admin/<team>/requalify/", **POST_REQUEST)
@api_response
def admin_requalify(team):
    return admin.requalify(ParsedRequest(request), team)


# view all users
@app.route("/admin/users/all/", strict_slashes=False)
@api_response
def all_users_secure():
    return admin.get_secure_user_data(ParsedRequest(request))


# view all teams
@app.route("/admin/teams/all", strict_slashes=False)
@api_response
def all_teams_secure():
    return admin.get_secure_team_data(ParsedRequest(request))


# ===========================================================================
# ===========================================================================
#                                   Tokens
@app.route("/users/passwords/reset/", **POST_REQUEST)
@api_response
def reset_password():
    return temp_tokens.api_forgot_password(ParsedRequest(request))


@app.route("/users/email/verify/", strict_slashes=False)
@api_response
def verify_email():
    return temp_tokens.api_verify_email(ParsedRequest(request))


@app.errorhandler(404)
def catch_all(e):
    return json_response({"error": "not found"})


@app.errorhandler(405)
def method_not_allowed(e):
    return json_response({"error": "Method not allowed"})


if __name__ == "__main__":
    app.run(debug=True)
