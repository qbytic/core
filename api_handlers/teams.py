from psycopg2 import IntegrityError

from app_init import TeamTable, UserTable
from auth_token import require_jwt
from constants import ALLOW_REMOVALS, ROLE_ID_DICT
from response_caching import cache
from util import AppException
from util import ParsedRequest as _Parsed
from util import map_to_list
from discord_integrations import set_roles


from .common import (
    add_to_db,
    clean_node,
    delete_from_db,
    get_clan_by_id,
    get_user_by_id,
    mutate,
    save_to_db,
)
from .cred_manager import CredManager
from .data_util import (
    EVENT_NAMES,
    GAMES,
    MAX_MEMBER_COUNT,
    init_user_event_dict,
    init_user_gaming_data_dict,
    init_user_music_data_dict,
)


def validate(registration_data: dict, event: str, game: str = None) -> dict:
    """Validate the user submitted, event-specific  data 
    we need to make sure that we don't receive any other keys in the form
    for gaming event, we will need extra routes
    Args:
        registration_data (dict): the json object to add to event data
        event (str): name of the event
    

    Returns:
        dict
    """
    if event == "music":
        return init_user_music_data_dict(registration_data)
    return {}


@require_jwt()
def register_for_game(request: _Parsed, game: str, creds: CredManager = CredManager):
    get = request.json.get
    game = get("gaming_event__game")
    data = get("registration_data")

    user = creds.user

    user_data = get_user_by_id(user)
    event = "gaming"
    team_data = user_data.team_data.get(event)
    if team_data is None:
        raise AppException("Please register for the event first")

    game_data = team_data.get("game_data") or {}

    reg_data = game_data.get(game)
    if reg_data is not None:
        raise AppException("Already submitted details!")
    mutate(team_data, "game_data", "game", init_user_gaming_data_dict(data, game))
    save_to_db()
    return {"user_data": user_data.as_json}


@require_jwt()
def create_team(request: _Parsed, team_event, creds: CredManager = CredManager):
    json = request.json
    get = json.get
    team_name = get("team_name")
    if team_event not in EVENT_NAMES:
        # bail out before hitting the db
        raise AppException("Event does not exist")

    registration_data = get("registration_data")
    user = get_user_by_id(creds.user)

    assert_user_is_clanless(user, team_event, prefix="You are")

    members = [creds.user]
    try:
        team = TeamTable(
            team_name=team_name,
            team_event=team_event,
            members=members,
            leader=creds.user,
        )
        user.team_data[team_event] = {
            "name": team_name,
            "registration_data": validate(registration_data, team_event),
        }

        add_to_db(team)
    except Exception as e:
        if isinstance(getattr(e, "orig", None), IntegrityError):
            raise AppException("clan name taken")
        raise e
    return {"clan_data": team.as_json}


@require_jwt(strict=False)
def get_team(request: _Parsed, clan: str, creds: CredManager = CredManager):
    user = creds.user
    clan_data = get_clan_by_id(clan)
    json = clan_data.as_json
    if user not in clan_data.members and not creds.is_admin:
        json.pop("_secure_")
    return {"clan_data": json}


@require_jwt()
def add_member(request: _Parsed, clan: str, creds: CredManager = CredManager):
    user = creds.user
    json = request.json
    to_add = json.get("user")
    if to_add == user:
        raise AppException("You cannot add yourself to a team!")

    clan_data = get_clan_by_id(clan)
    members = clan_data.members
    if user not in members and not creds.is_admin:
        raise AppException(f"You cannot edit settings for Clan {clan}")

    clan_event = clan_data.team_event
    maximum = MAX_MEMBER_COUNT.get(clan_event)
    if maximum == len(members):
        raise AppException(f"Clan has reached the max limit of players")

    addee_data = get_user_by_id(to_add)

    assert_user_is_clanless(addee_data, clan_event)

    clan_requests = clan_data.clan_requests
    if to_add in clan_requests:
        add_player_with_side_effects(clan_data, addee_data)

    else:
        # the player hasn't requested to join, invite them
        invites = addee_data.clan_invites.get(clan_event) or []

        if clan in invites:
            raise AppException("Already Invited!")
        add_player_invite(clan_data, addee_data)

    save_to_db()
    return {"clan_data": clan_data.as_json}


@require_jwt()
def remove_member(request: _Parsed, clan: str, creds: CredManager = CredManager):
    if not ALLOW_REMOVALS:
        raise AppException("Players can not be removed from the clan now!")
    user = creds.user
    json = request.json
    to_remove = json.get("user")
    clan_data = get_clan_by_id(clan)

    members = clan_data.members

    if user != clan_data.leader and not creds.is_admin:
        raise AppException(f"You cannot edit settings for Clan {clan}")

    if to_remove not in members:
        if to_remove not in clan_data.clan_requests:
            raise AppException(f"User is not a member of Clan {clan}")

        remove_player_request(clan_data, get_user_by_id(to_remove))
    else:
        remove_player_from_clan(clan_data, get_user_by_id(to_remove))

    if len(clan_data.members) == 0:
        delete_from_db(clan_data, True)

    save_to_db()
    data = clan_data.as_json
    if user == to_remove:
        data.pop("_secure_")
    return {"clan_data": data}


@require_jwt()
def request_to_join(
    request: _Parsed, clan: str, event_name: str, creds: CredManager = CredManager
):
    get = request.json.get
    user = creds.user
    user_data = get_user_by_id(user)

    registration_data = get("registration_data")

    assert_user_is_clanless(user_data, event_name, prefix="You are")

    maximum = MAX_MEMBER_COUNT.get(event_name)

    clan_data = get_clan_by_id(clan)
    if len(clan_data.members) == maximum:
        raise AppException(f"Clan {clan_data.team_name} already has {maximum} members")

    if user in clan_data.clan_invites:
        add_player_with_side_effects(clan_data, user_data)
    else:
        current_requests = clan_data.clan_requests
        if user in current_requests:
            raise AppException(f"You have already requested to join Clan {clan}")

        add_player_request(clan_data, user_data)

    add_registration_data(user_data, event_name, registration_data)

    save_to_db()
    return {"user_data": user_data.as_json}


@cache("team-list", 10)
def team_list():
    all_users = TeamTable.query.order_by(
        TeamTable.team_name != "admins", TeamTable.created_at.asc()
    ).all()
    return {"teams": map_to_list(clean_node, all_users)}


editable_fields = ("email", "school", "name")


def assert_user_is_clanless(user: UserTable, event: str, prefix=None):
    prefix = prefix or f"{user.user} is"
    clan = user.team_data.get(event)
    if clan is not None and clan.get("name") is not None:
        raise AppException(f"{prefix} already a member of {clan['name']}")


def add_player_with_side_effects(clan_data, user_data):
    add_player_to_clan(clan_data, user_data)
    remove_player_invite(clan_data, user_data)
    remove_player_request(clan_data, user_data)
    event_name = clan_data.team_event

    try:
        del user_data.clan_invites[event_name]
    except:
        pass

    try:
        del user_data.clan_requests[event_name]
    except:
        pass

    update_discord_roles(user_data)


def add_registration_data(
    user_data: UserTable, event_name: str, registration_data: dict = None
):
    if user_data.team_data[event_name].get("registration_data") is None:
        user_data.team_data["registration_data"] = validate(
            registration_data, event_name, None
        )


# remove clan sent invite from both clan data and user data
def remove_player_invite(clan_data: TeamTable, user_data: UserTable):
    _internal_remove_linked_data(clan_data, user_data, "clan_invites")


# remove user sent request from both clan data and user data
def remove_player_request(clan_data: TeamTable, user_data: UserTable):
    _internal_remove_linked_data(clan_data, user_data, "clan_requests")


def remove_player_from_clan(clan_data: TeamTable, user_data: UserTable):
    user_name = user_data.user

    members = clan_data.members
    if user_name in members:
        members.remove(user_name)
    event = clan_data.team_event
    clan_dict = user_data.team_data.get(event)
    if clan_dict is not None:
        mutate(user_data.team_data, event, "name", None)
    update_discord_roles(user_data)


def add_player_invite(clan_data: TeamTable, user_data: UserTable):
    _internal_add_linked_data(clan_data, user_data, "clan_invites")


def add_player_request(clan_data: TeamTable, user_data: UserTable):
    _internal_add_linked_data(clan_data, user_data, "clan_requests")


# add a player to clan
def add_player_to_clan(clan_data: TeamTable, user_data: UserTable):
    if user_data.user not in clan_data.members:
        clan_data.members.append(user_data.user)
    event = clan_data.team_event
    _dict = user_data.team_data.get(event)
    if _dict is None:
        user_data.team_data[event] = {}
    mutate(user_data.team_data, event, "name", clan_data.team_name)

    # if len(clan_data.members) == MAX_MEMBER_COUNT[event]:
    #     clan_data.clan_invites.clear()
    #     clan_data.clan_requests.clear()


def _internal_remove_linked_data(clan_data: TeamTable, user_data: UserTable, attr: str):
    # both remove_player_request and remove_player_invite do the exact same thing, just with different columns
    # so we abstract it out in a simple dynamic method

    user_name = user_data.user
    clan_name = clan_data.team_name
    event_name = clan_data.team_event

    clan_attribute_value_list: list = getattr(clan_data, attr)
    if user_name in clan_attribute_value_list:
        clan_attribute_value_list.remove(user_name)
    u_attr = getattr(user_data, attr)
    user_attribute_value_list: list = u_attr.get(event_name)
    if user_attribute_value_list is not None and clan_name in user_attribute_value_list:
        user_attribute_value_list.remove(clan_name)
        u_attr[event_name] = user_attribute_value_list


def _internal_add_linked_data(clan_data: TeamTable, user_data: UserTable, attr: str):
    user_name = user_data.user
    clan_name = clan_data.team_name
    event_name = clan_data.team_event

    clan_attribute = getattr(clan_data, attr)
    if user_name not in clan_attribute:
        clan_attribute.append(user_name)

    u_attr = getattr(user_data, attr)
    user_attr_value = u_attr.get(event_name) or []
    if clan_name not in user_attr_value:
        user_attr_value.append(clan_name)
        u_attr[event_name] = user_attr_value


def update_discord_roles(user_data: UserTable):
    roles = []
    for event, data in user_data.team_data.items():
        if data.get("name") is not None:
            roles.append(ROLE_ID_DICT[event])
    set_roles(user_data.discord_id, roles)

