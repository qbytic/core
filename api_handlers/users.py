from typing import List

from flask import request as flask_request
from psycopg2 import IntegrityError

from app_init import UserTable
from auth_token import (
    regenerate_access_token,
    issue_access_token,
    require_jwt,
    issue_refresh_token,
)
from danger import (
    ACCESS_TOKEN,
    REFRESH_TOKEN,
    check_password_hash,
    create_token,
    decode_token,
)
from discord_integrations import add_to_guild, exchange_code
from response_caching import cache
from util import AppException
from util import ParsedRequest as _Parsed
from util import json_response, map_to_list

from .common import add_to_db, clean_node, get_user_by_id, save_to_db
from .cred_manager import CredManager
from .data_util import init_user_event_dict


def register(request: _Parsed):
    json = request.json
    get = json.get
    user = get("user")
    name = get("name")
    email = get("email")
    school = get("school")
    password = get("password")
    # this data is signed to stop registration if we catch any tampering
    # as this is user's data, it's not an issue sending it back to them
    signed_discord_data = decode_token(get("signed_discord"))

    discord_id = signed_discord_data["discord_id"]
    discord_access_token = signed_discord_data["access"]
    discord_refresh_token = signed_discord_data["refresh"]
    discord_token_expires_in = signed_discord_data["expires"]

    try:
        user_data = UserTable(
            user=user,
            name=name,
            email=email,
            school=school,
            password=password,
            team_data=init_user_event_dict(),
            discord_id=discord_id,
            discord_access_token=discord_access_token,
            discord_refresh_token=discord_refresh_token,
            discord_token_expires_in=discord_token_expires_in,
        )
        add_to_guild(user_data)
        add_to_db(user_data)
        return user_data.as_json
    except Exception as e:
        if isinstance(getattr(e, "orig", None), IntegrityError):
            raise AppException("User exists")
        raise e


def login(request: _Parsed):
    json = request.json
    get = json.get
    user = get("user", "").strip()
    password = get("password", "")
    invalids = []
    if not user:
        invalids.append("username")
    if not password:
        invalids.append("password")
    if invalids:
        raise AppException(f"Invalid {' and '.join(invalids)}")
    user_data = get_user_by_id(user)
    password_hash = user_data.password_hash
    if not check_password_hash(password_hash, password):
        raise AppException("Incorrect Password")
    username = user_data.user
    access_token = create_token(issue_access_token(username, user_data.is_admin))

    refresh_token = create_token(issue_refresh_token(username, password_hash))

    return json_response(
        {"success": True, "user_data": user_data.as_json},
        headers={"x-access-token": access_token, "x-refresh-token": refresh_token},
    )


def re_authenticate(req: _Parsed):
    headers = flask_request.headers
    access_token = headers.get("x-access-token")
    decoded_access = decode_token(access_token)

    if decoded_access is None:
        refresh_token = headers.get("x-refresh-token")
        decoded_refresh = decode_token(refresh_token)
        access, refresh = regenerate_access_token(decoded_refresh)
        if access is None:
            raise AppException("re-auth")

        return json_response(
            {},
            headers={
                "x-access-token": create_token(access),
                "x-refresh-token": create_token(refresh),
            },
        )


def get_discord_token(req: _Parsed):
    code = req.json["code"]
    data = exchange_code(code)
    discord_token = create_token(data["token"])
    return {"token": discord_token, "autofill": data["autofill"]}


# creds  will be injected by require_jwt
@require_jwt(strict=False)
def get_user_details(request: _Parsed, user: str, creds: CredManager = CredManager):
    current_user = creds.user
    if user == "me" or current_user == user.lower():
        if current_user is not None:
            return self_details(request, creds)
        raise AppException("Not Authenticated")
    user_details = get_user_by_id(user)
    json = user_details.as_json
    json.pop("_secure_")
    return json


def self_details(request: _Parsed, creds: CredManager):
    req = get_user_by_id(creds.user)
    resp = req.as_json
    return {"user_data": resp}


@cache("user-list", 15)
def user_list():
    all_users: List[UserTable] = UserTable.query.order_by(
        UserTable.is_admin.asc(), UserTable.created_at.asc()
    ).all()
    return {"users": map_to_list(clean_node, all_users)}


@require_jwt()
def edit(request: _Parsed, user: str, creds: CredManager = CredManager):
    editable_fields = ("email", "school", "name")
    current_user = creds.user
    if user != current_user:
        raise AppException("Cannot edit ( not allowed )")
    json = request.json
    edit_field = json.get("field")
    if edit_field not in editable_fields:
        raise AppException("Requested field cannot be edited")
    new_value = json.get("new_value")
    user_data = get_user_by_id(current_user)

    setattr(user_data, edit_field, new_value)
    save_to_db()
    return user_data.as_json
