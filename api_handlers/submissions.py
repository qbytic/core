from urllib.parse import urlparse

from auth_token import require_jwt
from constants import EVENTS_REQUIRING_SUBMISSION
from util import AppException
from util import ParsedRequest as _Parsed
from util import map_to_list

from .common import get_clan_by_id, get_user_by_id, save_to_db
from .cred_manager import CredManager


def validate_file(event, data):
    # APPROVED_DOMAINS = ("drive.google.com", "pastebin.com", "discord.com")
    if event not in EVENTS_REQUIRING_SUBMISSION:
        raise AppException("Invalid event!")
    parsed = urlparse(data)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        raise AppException("Invalid URL")


@require_jwt()
def submit(request: _Parsed, event: str, team_name: str, creds=CredManager):
    json: dict = request.json
    submit_data = json["data"]
    submission_round = json["round"]

    validate_file(event, submit_data)

    team_data = get_clan_by_id(team_name)
    if creds.user != team_data.leader:
        raise AppException("Only the clan leader can submit")

    if len(team_data.submissions) > submission_round:
        raise AppException("Already submitted!")

    if team_data.current_round != submission_round:
        raise AppException("Invalid level")

    team_data.submissions.append(submit_data)
    save_to_db()
    return {"team_data": team_data.as_json}
