from typing import List

from flask import request as flask_request
from psycopg2 import IntegrityError

from app_init import UserTable
from auth_token import (
    issue_access_token,
    issue_refresh_token,
    regenerate_access_token,
    require_jwt,
)
from danger import (
    ACCESS_TOKEN,
    REFRESH_TOKEN,
    check_password_hash,
    create_token,
    decode_token,
)
from discord_integrations import exchange_code
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

    try:
        user_data = UserTable(
            user=user,
            name=name,
            email=email,
            school=school,
            password=password,
            team_data=init_user_event_dict(),
        )
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


@require_jwt()
def setup_discord(request: _Parsed, creds=CredManager):
    user = get_user_by_id(creds.user)
    if all(
        x
        for x in (
            user.discord_id,
            user.discord_access_token,
            user.discord_refresh_token,
            user.discord_token_expires_in,
        )
    ):
        raise AppException("Discord already linked!!")
    code = request.json["code"]

    discord_response = exchange_code(code)

    access = discord_response["access"]
    refresh = discord_response["refresh"]
    expires = discord_response["expires"]
    discord_id = discord_response["discord_id"]

    user.discord_id = discord_id
    user.discord_access_token = access
    user.discord_refresh_token = refresh
    user.discord_token_expires_in = expires

    save_to_db()

    return {"user_data": user.as_json}


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
    return {"user_data": json}


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


@require_jwt()
def check_auth(creds=CredManager):
    return {"user_name": creds.user}

