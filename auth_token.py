"""Decorators that ensure authentication is provided
"""
from flask import request, make_response, Response
from danger import (
    decode_token as decode,
    ACCESS_TOKEN,
    REFRESH_TOKEN,
    check_password_hash as check,
    generate_password_hash,
)
from api_handlers.common import get_user_by_id
from util import AppException, json_response, ParsedRequest
from api_handlers.cred_manager import CredManager


def require_jwt(strict=True):
    # use this wherever you need the user to provide authentication data
    # pass strict=True if you absolutely need an authenticated user to access the route
    def wrapper(func):
        def run(*args, **kwargs):
            access = get_token(strict=strict)
            kwargs["creds"] = CredManager(access)

            return func(*args, **kwargs)

        return run

    return wrapper


def regenerate_access_token(refresh: dict) -> dict:
    user = refresh.get("user")
    integrity = refresh.get("integrity")
    data = get_user_by_id(user)
    current = data.user + data.password_hash
    if check(integrity, current):
        return (
            issue_access_token(user, data.is_admin),
            issue_refresh_token(user, data.password_hash),
        )
    return None, None


def issue_access_token(username: str, is_admin: bool):
    return {"token_type": ACCESS_TOKEN, "user": username, "is_admin": is_admin}


def issue_refresh_token(username, password_hash):
    return {
        "token_type": REFRESH_TOKEN,
        "user": username,
        "integrity": generate_password_hash(username + password_hash),
    }


def get_token(strict=True):
    headers = request.headers
    # should just use Authorization here...
    received_access_token = headers.get("x-access-token")

    if not received_access_token:
        if strict:
            raise AppException("No authentication provided")
        return None
    try:
        access = decode(received_access_token)
    except Exception:
        if strict:
            raise AppException("Invalid token")
        return None

    if access is None:
        if strict:
            raise AppException("refresh")
        return None

    return access

