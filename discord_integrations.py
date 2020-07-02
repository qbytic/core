from time import time

import requests

from constants import (
    DISCORD_BOT_TOKEN,
    DISCORD_CLIENT_ID,
    DISCORD_SECRET,
    GUILD_ID,
    IS_HEROKU,
    PARTICIPANT_ROLE_ID,
)
from util import AppException

# from api_handlers.common import save_to_db

APP_SCOPE = "email identify guilds.join"
API_ENDPOINT = "https://discord.com/api/v6"
_URI = "https://qbytic.com" if IS_HEROKU else "http://localhost:4200"

REDIRECT_URI = f"{_URI}/u/-/discord/auth/flow/signup"


class TokenAuth(requests.auth.AuthBase):
    def __init__(self, token, auth_type="Bearer"):
        self.token = token
        self.auth_type = auth_type

    def __call__(self, r):
        r.headers["Authorization"] = f"{self.auth_type} { self.token}"
        return r


def ensure_fresh_token(func):
    def wrapper(*args):
        user_data = args[0]
        expires_in = user_data.discord_token_expires_in
        if time() >= expires_in:
            data = refresh_token(user_data.discord_refresh_token)
            user_data.discord_access_token = data["access"]
            user_data.discord_refresh_token = data["refresh"]
            user_data.discord_token_expires_in = data["expires"]
        return func(*args)

    return wrapper


def _post_to_discord(data):
    r = requests.post(f"{API_ENDPOINT}/oauth2/token", data=data)

    if not r.ok:
        print(r.text)
        # return
        raise AppException("Discord api gave invalid response")
    js = r.json()
    return {
        "access": js["access_token"],
        "refresh": js.get("refresh_token"),
        "expires": js["expires_in"],
        "token_type": "discord",
    }


def exchange_code(code: str) -> dict:
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": APP_SCOPE,
    }
    return query_user(_post_to_discord(data))


def refresh_token(refresh_token: str) -> dict:
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "redirect_uri": REDIRECT_URI,
        "scope": APP_SCOPE,
    }
    return _post_to_discord(data)


def query_user(data: dict) -> dict:
    access = data["access"]
    req = requests.get(f"{API_ENDPOINT}/users/@me", auth=TokenAuth(access))
    js = req.json()
    if not req.ok:
        print(js)
        raise AppException("Error while fetching user data from discord")
    data["discord_id"] = js["id"]
    return {
        "autofill": {"username": js["username"], "email": js["email"]},
        "token": data,
    }


@ensure_fresh_token
def add_to_guild(user_data):
    user_id = user_data.discord_id
    access = user_data.discord_access_token
    _add_to_guild(user_id, access)


def _add_to_guild(user_id, access):
    url = f"{API_ENDPOINT}/guilds/{GUILD_ID}/members/{user_id}"
    req = requests.put(
        url,
        json={"access_token": access, "roles": [PARTICIPANT_ROLE_ID]},
        auth=TokenAuth(DISCORD_BOT_TOKEN, "Bot"),
    )
    return _assert_success(req)


@ensure_fresh_token
def set_roles(user_data, roles: list):
    user_id = user_data.discord_id
    access = user_data.discord_access_token
    return _set_roles(user_id, access, roles)


def _set_roles(user_id, access, roles):
    url = f"{API_ENDPOINT}/guilds/{GUILD_ID}/members/{user_id}"
    roles.append(PARTICIPANT_ROLE_ID)
    req = requests.patch(
        url,
        json={"access_token": access, "roles": roles},
        auth=TokenAuth(DISCORD_BOT_TOKEN, "Bot"),
    )
    return _assert_success(req)


# DO NOT THROW HERE AS DISCORD CAN AND WILL FAIL FOR SOME REASONS
# LIKE USER REVOKING PERMISSIONS
# EXPECT THOSE


def _assert_success(req):
    if not req.ok:
        print(req.json())
        # raise AppException("Could not add to server")
        return False
    return True
