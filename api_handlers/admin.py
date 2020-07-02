from app_init import TeamTable, UserTable
from auth_token import require_jwt
from util import AppException, ParsedRequest

from .common import get_clan_by_id, get_config, get_user_by_id, query_all, save_to_db
from .cred_manager import CredManager


def require_admin(func):
    @require_jwt()
    def wrapper(*args, **kwargs):
        creds = kwargs["creds"]
        if not creds.is_admin:
            raise AppException("Not authorized")

        return func(*args, **kwargs)

    return wrapper


SUCCESS = {"success": True}


@require_admin
def score_team(request: ParsedRequest, team, creds=CredManager):
    json = request.json
    team_data = get_clan_by_id(team)
    score = int(json["score"])
    if not 0 <= score <= 20:
        raise AppException("Invalid value of score")
    round_num = int(json["round"])
    if team_data.current_round != round_num:
        raise AppException("User has already been rated for this round")
    # validate_score(score,team_data.team_event)
    # if only allow scores  5+ to progress
    if score > 5 and get_config(team_data.team_event).number_of_rounds < round_num:
        team_data.current_round += 1
    team_data.score.append(score)
    save_to_db()
    return SUCCESS


@require_admin
def disqualify(request: ParsedRequest, team, creds=CredManager):

    reason = request.json["reason"].strip()

    team_data = get_clan_by_id(team)
    if team_data.is_disqualifed:
        raise AppException("Already disqualified")
    team_data.is_disqualified = True
    team_data.disqualification_reason = reason
    save_to_db()
    return SUCCESS


@require_admin
def requalify(request: ParsedRequest, team, creds=CredManager):

    team_data = get_clan_by_id(team)
    if not team_data.is_disqualifed:
        raise AppException("Team not disqualified")
    team_data.is_disqualified = False
    save_to_db()
    return SUCCESS


@require_admin
def delete_user(request: ParsedRequest, team, creds=CredManager):
    raise NotImplementedError


@require_admin
def delete_team(request: ParsedRequest, team, creds=CredManager):
    raise NotImplementedError


@require_admin
def get_secure_team_data(request: ParsedRequest, creds=CredManager):
    return {"clans": query_all(TeamTable)}


@require_admin
def get_secure_user_data(request: ParsedRequest, creds=CredManager):
    return {"users": query_all(UserTable)}
