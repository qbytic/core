from time import time

from app_init import UserTable
from auth_token import require_jwt
from danger import (
    check_password_hash,
    create_token,
    decode_token,
    generate_password_hash,
)
from util import AppException, ParsedRequest

from .common import get_user_by_id, save_to_db
from .cred_manager import CredManager
from .email_manager import send_email

THREE_HOURS = 3 * 60 * 60


def create_email_verification_token(user: UserTable):
    # email = user.email
    # send_email
    token = {"u": user.user, "e": user.email, "exp": time() + THREE_HOURS}
    return create_token(token)


def verify_email(token: str):
    token = decode_token(token)
    assert_token_is_valid(token)
    user = token["u"]
    user_data = get_user_by_id(user)
    if user_data.email == token["e"]:
        user_data.has_verified_email = True
        save_to_db()
        return True
    raise AppException("Could not verify email")


def create_password_verification_token(user: UserTable):
    token = {
        "u": user.user,
        "ch": generate_password_hash(user.user + user.password_hash),
        "exp": time() + THREE_HOURS,
    }
    return create_token(token)


def verify_password(token: str, new_password: str):
    token = decode_token(token)
    assert_token_is_valid(token)

    user = token["u"]
    user_data = get_user_by_id(user)
    if not check_password_hash(token["ch"], user_data.user + user_data.password_hash):
        raise AppException("Password already changed!")

    user_data.password_hash = new_password
    save_to_db()


def assert_token_is_valid(token: dict):
    if token is None:
        raise AppException("Token Expired")


def api_forgot_password(req: ParsedRequest):
    json = req.json
    user = json["user"]
    data = get_user_by_id(user)
    token = create_password_verification_token(data)
    send_email(token, "password", data.email)
    return {"success": True}


@require_jwt()
def api_verify_email(req: ParsedRequest, creds=CredManager):
    data = get_user_by_id(creds.user)
    token = create_email_verification_token(data)
    send_email(token, "email", data.email)
    return {"success": True}
