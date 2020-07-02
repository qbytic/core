from os import environ
from re import compile as cmpl
from time import time
from typing import Dict, List, Union

from flask import Flask, Response, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList

from constants import EVENT_NAMES
from danger import check_password_hash, generate_password_hash
from set_env import setup_env
from util import AppException, get_origin, safe_mkdir, sanitize, validate_email_address

setup_env()


app = Flask(__name__)
app.secret_key = environ.get("FLASK_SECRET")
database_url: str = environ.get("DATABASE_URL")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
safe_mkdir("@cache")

ONE_YEAR_IN_SECONDS = 60 * 60 * 24 * 365


@app.route("/robots.txt")
def index():
    # we disallow all bots here because we don't want useless crawling over the API
    return send_from_directory("static", "robot.txt", cache_timeout=ONE_YEAR_IN_SECONDS)


EXPOSE_HEADERS = ", ".join(("x-access-token", "x-refresh-token", "x-dynamic"))


@app.after_request
def cors(resp):
    origin = get_origin(request)
    resp.headers["access-control-allow-origin"] = origin
    resp.headers["access-control-allow-headers"] = request.headers.get(
        "access-control-request-headers", "*"
    )
    resp.headers["access-control-allow-credentials"] = "true"
    resp.headers["x-dynamic"] = "true"
    resp.headers["access-control-max-age"] = "86400"
    resp.headers["access-control-expose-headers"] = EXPOSE_HEADERS
    return resp


ListOfStrings = List[str]
SubmissionType = List[Dict[str, Dict]]
TeamData = Dict[str, Dict[str, str]]
InvitesOrRequests = Dict[str, ListOfStrings]
ListOfDict = List[Dict]
ListOfInt = List[int]


class UserTable(db.Model):
    # we are actually requesting the ID not the username
    _discord_id_re = cmpl(r"^\d+$").search
    # pylint: disable=E1101
    # these type hints are actually false, but they do help with the IDE
    user: str = db.Column(db.String(30), primary_key=True)
    name: str = db.Column(db.String(30), nullable=False)
    email: str = db.Column(db.String, unique=True, nullable=False)
    school: str = db.Column(db.String(30))
    password_hash: str = db.Column(db.String, nullable=False)
    team_data: TeamData = db.Column(MutableDict.as_mutable(JSONB), nullable=False)
    # ================================================================
    #                          Discord Specific
    discord_id: str = db.Column(db.String, unique=True, nullable=False)
    discord_access_token: str = db.Column(db.String, nullable=False)
    discord_refresh_token: str = db.Column(db.String, nullable=False)
    discord_token_expires_in: int = db.Column(db.Integer, nullable=False)
    # ================================================================
    # =================================================================
    #                          Additional
    created_at: int = db.Column(db.Integer)
    is_admin: bool = db.Column(db.Boolean)
    has_verified_email: bool = db.Column(db.Boolean)
    clan_invites: InvitesOrRequests = db.Column(MutableDict.as_mutable(JSONB))
    # list of users that want to join the clan
    clan_requests: InvitesOrRequests = db.Column(MutableDict.as_mutable(JSONB))
    # =================================================================
    # pylint: enable=E1101

    @property
    def as_json(self):
        return {
            "name": self.name,
            "user": self.user,
            "school": self.school,
            "team_data": self.team_data,
            "is_admin": self.is_admin,
            "has_verified_email": self.has_verified_email,
            "created_at": self.created_at,
            "_secure_": {
                "email": self.email,
                "discord_id": self.discord_id,
                "clan_invites": self.clan_invites,
                "clan_requests": self.clan_requests,
            },
        }

    def __init__(
        self,
        user: str = None,
        name: str = None,
        email: str = None,
        school: str = None,
        password: str = None,
        team_data: TeamData = {},
        discord_id: str = None,
        discord_access_token: str = None,
        discord_refresh_token: str = None,
        discord_token_expires_in: int = None,
        is_admin: bool = False,
        is_disqualified: bool = False,
        disqualification_reason: str = None,
        has_verified_email: bool = False,
        clan_invites: InvitesOrRequests = {},
        clan_requests: InvitesOrRequests = {},
        created_at: int = None,
    ):
        raise_if_invalid_data(
            user,
            name,
            email,
            password,
            discord_id,
            discord_access_token,
            discord_refresh_token,
        )
        self.user = user.lower()
        self.name = name
        self.email = email
        self.school = school
        # NOTE We Will hash the password (check __setattr__)
        self.password_hash = password
        self.team_data = team_data or {}
        self.discord_id = discord_id
        self.discord_access_token = discord_access_token
        self.discord_refresh_token = discord_refresh_token
        self.discord_token_expires_in = discord_token_expires_in
        self.is_admin = is_admin
        self.has_verified_email = has_verified_email
        self.clan_invites = clan_invites
        self.clan_requests = clan_requests
        self.created_at = time()

    def __setattr__(self, key: str, val):
        """Checks for data type validity before passing it to
            the database
        Args:
            key (str)
            val (Any)

        Raises:
            ValueError: An error when the passed data doesn't satisfy the constraints.
                        It can be wrapped in str() and returned back to client
        """
        # if the value is same, don't attempt any SQL operation
        if self._is_same_value(key, val):
            return

        if key == "password_hash":
            self._validate_password(val)
            val = generate_password_hash(val)
        else:
            if key == "user":
                self._validate_user(val)

            if key == "discord_token_expires_in":
                val = int(time() + int(val))

            elif key == "discord_id":
                self._validate_discord(val)

            elif key == "email":
                self._validate_email(val)
                # we unverify the email everytime it changes
                super().__setattr__("has_verified_email", False)

        super().__setattr__(key, val)

    def _validate_user(self, user: str):
        length = len(user)
        if length > 30:
            raise AppException("Username cannot be longer than 30 characters")
        if length < 4:
            raise AppException("Username cannot be shorter than 4 characters")
        if sanitize(user) != user:
            raise AppException("Username cannot have special characters or whitespace")

    def _validate_password(self, password: str):
        length = len(password)
        if length < 4:
            raise AppException("Password cannot be shorter than 4 characters")

    def _validate_discord(self, tag: str):
        if self._discord_id_re(tag) is None:
            raise AppException("Invalid discord ID")

    def _validate_email(self, mail: str):
        validate_email_address(mail)

    def _is_same_value(self, key: str, val) -> bool:
        if hasattr(self, key):
            previous_value = super().__getattribute__(key)

            return (
                (previous_value and check_password_hash(previous_value, val))
                if key == "password_hash"
                else previous_value == val
            )


class TeamTable(db.Model):
    MAX_MEMBER_COUNT = 5
    __inited: bool = False
    # pylint: disable=E1101
    team_name: str = db.Column(db.String(30), nullable=False, primary_key=True)
    team_event: str = db.Column(db.String(30), nullable=False)
    # list of player usernames that are a part of this team
    members: ListOfDict = db.Column(MutableList.as_mutable(ARRAY(db.String(30))))
    # leader of the team, by default the player who created the clan
    leader: str = db.Column(db.String(30), nullable=False)
    # list of users that this clan has invited
    clan_invites: ListOfStrings = db.Column(
        MutableList.as_mutable(ARRAY(db.String(30)))
    )
    # list of users that want to join the clan
    clan_requests: ListOfStrings = db.Column(
        MutableList.as_mutable(ARRAY(db.String(30)))
    )
    # mapping of the event names and their scores and the required data
    event_data: Dict = db.Column(MutableDict.as_mutable(JSONB), nullable=False)
    is_disqualified: bool = db.Column(db.Boolean)
    disqualification_reason: str = db.Column(db.String(400))
    created_at: int = db.Column(db.Integer)
    current_round: int = db.Column(db.Integer)
    submissions: SubmissionType = db.Column(MutableDict.as_mutable(JSONB))
    score: ListOfInt = db.Column(MutableList.as_mutable(ARRAY(db.Integer)))

    # pylint: enable=E1101

    @property
    def as_json(self):
        return {
            "name": self.team_name,
            "event": self.team_event,
            "members": self.members,
            "leader": self.leader,
            "is_disqualified": self.is_disqualified,
            "disqualification_reason": self.disqualification_reason,
            "created_at": self.created_at,
            "current_round": self.current_round,
            "score": self.score,
            "_secure_": {
                "clan_invites": self.clan_invites,
                "clan_requests": self.clan_requests,
                "event_data": self.event_data,
                "submissions": self.submissions,
            },
        }

    def __init__(
        self,
        team_name: str = None,
        team_event: str = None,
        members: ListOfStrings = None,
        leader: str = None,
        clan_invites: ListOfStrings = [],
        clan_requests: ListOfStrings = [],
        event_data: dict = {},
        is_disqualified: bool = False,
        disqualification_reason: str = None,
        created_at: int = None,
        current_round: int = 0,
        submissions: SubmissionType = [],
        score: ListOfInt = [],
    ):
        raise_if_invalid_data(team_name, members)
        self.team_name = team_name
        self.team_event = team_event
        # validate members before adding
        self.members = members
        self.leader = leader
        self.clan_invites = clan_invites
        self.clan_requests = clan_requests
        self.event_data = event_data
        self.is_disqualified = is_disqualified
        self.disqualification_reason = disqualification_reason
        self.created_at = time()
        self.current_round = current_round
        self.submissions = submissions
        self.score = score
        self.__inited = True

    def _is_same_value(self, key: str, val) -> bool:
        if hasattr(self, key):
            previous_value = super().__getattribute__(key)

            return (
                (previous_value and check_password_hash(previous_value, val))
                if key == "password_hash"
                else previous_value == val
            )

    def _validate_team_name(self, val):
        val_len = len(val)
        if val_len > 80:
            raise AppException("Team name must be less than 30 characters")
        if val_len < 4:
            raise AppException("Team name must be atleast 4 characters")
        if sanitize(val) != val:
            raise AppException("Invalid characters in team name")

    def __setattr__(self, key: str, val):
        if self._is_same_value(key, val):
            return

        if key == "team_event":
            if val not in EVENT_NAMES:
                raise AppException(f"Invalid Event name {val}")

        if key == "team_name":
            val = val.lower()
            self._validate_team_name(val)

        if key == "is_disqualified" and not val:
            # if we are requalifying someone, also clear the disqualification reason
            if self.__inited:
                super().__setattr__("disqualification_reason", None)
        if key == "members" and len(val) > 5:
            raise AppException("Team can only have 5 players at amx")
        super().__setattr__(key, val)


ConfigType = Dict[str, Union[Dict, str]]


class EventConfig(db.Model):
    # pylint: disable=E1101
    event_name: str = db.Column(db.String(30), primary_key=True)
    number_of_rounds: int = db.Column(db.Integer, nullable=False)
    config: ConfigType = db.Column(MutableDict.as_mutable(JSONB))
    # pylint: enable=E1101
    def __init__(
        self,
        event_name: str = None,
        number_of_rounds: int = None,
        config: ConfigType = None,
    ):
        self.event_name = event_name
        self.number_of_rounds = number_of_rounds
        self.config = config


def raise_if_invalid_data(*args):
    if any(not x or not ((x).strip() if isinstance(x, str) else True) for x in args):
        raise AppException("Invalid Data")
