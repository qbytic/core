from api_handlers import admin
from app_init import app
from util import POST_REQUEST, ParsedRequest, api_response, json_response

# ===========================================================================
# ===========================================================================
#                                  Admin

# rate a submission
@app.route("/admin/<team>/score/", **POST_REQUEST)
@api_response
def admin_score(team):
    return admin.score_team(ParsedRequest(), team)


@app.route("/admin/<team>/disqualify/", **POST_REQUEST)
@api_response
def admin_disqualify(team):
    return admin.disqualify(ParsedRequest(), team)


@app.route("/admin/<team>/requalify/", **POST_REQUEST)
@api_response
def admin_requalify(team):
    return admin.requalify(ParsedRequest(), team)


# view all users
@app.route("/admin/users/all/", strict_slashes=False)
@api_response
def all_users_secure():
    return admin.get_secure_user_data(ParsedRequest())


# view all teams
@app.route("/admin/teams/all/", strict_slashes=False)
@api_response
def all_teams_secure():
    return admin.get_secure_team_data(ParsedRequest())
