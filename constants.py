from os import environ as _environ
from set_env import setup_env as _setup_env


_setup_env()

IS_HEROKU = _environ.get("IS_HEROKU") is not None
# discord specific
DISCORD_CLIENT_ID = _environ["DISCORD_CLIENT_ID"]

DISCORD_SECRET = _environ["DISCORD_SECRET"]

DISCORD_BOT_TOKEN = _environ["DISCORD_BOT_TOKEN"]

PARTICIPANT_ROLE_ID = _environ["DISCORD_PARTICIPANT_ROLE"]

GUILD_ID = _environ["DISCORD_GUILD_ID"]

ALLOW_REMOVALS = _environ.get("NO_REMOVE") is None
# JWT Signing key, make sure this stays same or every user will need to relogin
SIGNING_KEY = _environ.get("JWT_SIGNING_KEY")
# How long an access_token will last
TOKEN_EXPIRATION_TIME_IN_SECONDS = 60 * int(_environ.get("TOKEN_EXPIRATION_TIME"))

EVENT_NAMES = ("gaming", "prog", "pentest", "lit", "music", "video", "minihalo")
ROLE_ID_DICT = dict(
    zip(
        EVENT_NAMES,
        (
            _environ["DISCORD_GAMING_ROLE"],
            _environ["DISCORD_PROGRAMMING_ROLE"],
            _environ["DISCORD_PENTESTING_ROLE"],
            _environ["DISCORD_LITERATURE_ROLE"],
            _environ["DISCORD_MUSIC_ROLE"],
            _environ["DISCORD_VIDEO_ROLE"],
            _environ["DISCORD_CRYPTIC_ROLE"],
        ),
    )
)


def _remove_from(item: list, removables: list):
    return tuple(map(lambda x: x not in removables, item))


EVENTS_REQUIRING_SUBMISSION = _remove_from(EVENT_NAMES, ("gaming", "minihalo"))

MAIL_USERNAME = _environ["MAIL_USER"]
MAIL_PASS = _environ["MAIL_PASS"]

del _remove_from
del _environ
