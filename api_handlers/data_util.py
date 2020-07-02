from app_init import db, TeamTable, UserTable
from constants import EVENT_NAMES
from util import AppException
from os import environ

# do not store these in database as this is data is only specific to a particular event (music)
# and we can easily get away with a simple dicitonary access
MAX_MEMBER_COUNT = {
    x: int(environ.get(f"{x}_max_players", TeamTable.MAX_MEMBER_COUNT))
    for x in EVENT_NAMES
}
del environ


def init_user_event_dict(
    gaming_data: str = None,
    prog: str = None,
    pentest: str = None,
    lit: str = None,
    music: str = None,
    video: str = None,
    minihalo: str = None,
):
    """
    return dictionary of same shape, instead of creating them inline

    Args:
        gaming_data (str, optional): 
        prog (str, optional): 
        pentest (str, optional): 
        lit (str, optional): 
        music (str, optional): 
        video (str, optional): 
        minihalo (str, optional): 

    Returns:
        [dict]: `{
        "gaming": None,
        "prog": None,
        "pentest": None,
        "lit": None,
        "music": None,
        "video": None,
        "minihalo": None,
    }`
    """

    return dict(
        zip(EVENT_NAMES, (gaming_data, prog, pentest, lit, music, video, minihalo))
    )


def _csgo_shape(user: str = None, steam_id: str = None):
    return {"user": user, "steam_id": steam_id}


def _minecraft_shape(user: str = None, minecraft_id: str = None):
    return {"user": user, "minecraft_id": minecraft_id}


def _pubg_shape(user: str = None, pubg_id: str = None):
    return {"user": user, "pubg_id": pubg_id}


def _fortnite_shape(user: str = None, fortnite_id: str = None):
    return {"user": user, "fortnite_id": fortnite_id}


GAME_SHAPES = {
    "csgo": _csgo_shape,
    "minecraft": _minecraft_shape,
    "pubg": _pubg_shape,
    "fortnite": _fortnite_shape,
}

GAMES = tuple(GAME_SHAPES.keys())


def init_user_gaming_data_dict(kwargs, game: str = None) -> dict:
    if game not in GAMES:
        raise AppException(f"Invalid Game {game}")
    func = GAME_SHAPES[game]
    return ensure_safe(func(**kwargs))


def music_shape(
    artist_name: str = None,
    daw_used: str = None,
    music_platform_link: str = None,
    category: str = None,
) -> dict:
    if category not in ("edm", "lofi"):
        raise AppException("Invalid Music category")
    return {
        "artist_name": artist_name,
        "daw_used": daw_used,
        "music_platform_link": music_platform_link,
        "category": category,
    }


def init_user_music_data_dict(kwargs) -> dict:
    return ensure_safe(music_shape(**kwargs))


def ensure_safe(d: dict):
    if any(x is None or not isinstance(x, str) or len(x) > 1000 for x in d.values()):
        raise AppException("Invalid data")
