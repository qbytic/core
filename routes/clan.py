from app_init import app
from api_handlers import teams
from util import POST_REQUEST, ParsedRequest, api_response, json_response

# ===========================================================================
# ===========================================================================
#                            Teams

# create clan for a particular event
@app.route("/<event>/clans/create/", **POST_REQUEST)
@api_response
def create_team(event):
    return teams.create_team(ParsedRequest(), event)


# view clan info
@app.route("/clans/<clan>/data/", strict_slashes=False)
@api_response
def get_team(clan):
    return teams.get_team(ParsedRequest(), clan)


# invite a member or accept an invite
@app.route("/clans/<clan>/members/invite/", **POST_REQUEST)
@app.route("/clans/<clan>/members/add/", **POST_REQUEST)
@api_response
def add_member(clan):
    return teams.add_member(ParsedRequest(), clan)


# reject a member's request to join the clan
# or remove existing member from clan
@app.route("/clans/<clan>/members/reject/", **POST_REQUEST)
@app.route("/clans/<clan>/members/remove/", **POST_REQUEST)
@api_response
def remove_member(clan):
    return teams.remove_member(ParsedRequest(), clan)


# request to join a clan
# or join a clan that has invited you
@app.route("/<event>/clans/<clan>/request/", strict_slashes=False)
@app.route("/<event>/clans/<clan>/join/", strict_slashes=False)
@api_response
def request_to_join(event, clan):
    return teams.request_to_join(ParsedRequest(), clan, event)


@app.route("/<event>/clans/<clan>/submit/", **POST_REQUEST)
@api_response
def submit_proj(event, clan):
    return submissions.submit(ParsedRequest(), event, clan)


# register for a gaming event
@app.route("/g/gaming/<game>/register/", **POST_REQUEST)
@api_response
def register_game(game):
    return teams.register_for_game(ParsedRequest(), game)


# clan leaderabord
@app.route("/clans/all/", strict_slashes=False)
@api_response
def all_teams():
    return teams.team_list()
