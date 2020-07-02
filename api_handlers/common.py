from typing import Union

from sqlalchemy import func as _func

from app_init import EventConfig as _E
from app_init import TeamTable as _T
from app_init import UserTable as _U
from app_init import db as _db
from util import AppException as _AppException
from util import sanitize

lower = _func.lower
count = _func.count


# pylint: disable=E1101
def add_to_db(data, batch=False):
    _db.session.add(data)
    not batch and save_to_db()


def query_all(table):
    return table.query.all()


def save_to_db():
    _db.session.commit()


def delete_from_db(d, batch=False):
    if d:
        _db.session.delete(d)
        not batch and save_to_db()


def get_user_by_id(idx: str) -> _U:
    if not idx or sanitize(idx) != idx:
        return _assert_exists(None)
    return _assert_exists(_U.query.filter(lower(_U.user) == lower(idx)).first())


def get_clan_by_id(idx: str) -> _T:
    if not idx or sanitize(idx) != idx:
        return _assert_exists(None, "Clan")
    return _assert_exists(
        _T.query.filter(lower(_T.team_name) == lower(idx)).first(), "Clan"
    )


def get_config(name: str) -> _E:
    if not name or sanitize(name) != name:
        return _assert_exists(None, "Event")
    return _assert_exists(_E.query.filter_by(event_name=name).first(), "Event")


def get_table_size(table_attr):
    return _db.session.query(count(table_attr)).scalar()


def _assert_exists(user: _U, name="User"):
    if user is None:
        raise _AppException(f"{name} does not exist")
    return user


def mutate(obj: dict, dictionary_key: str, internal_key: str, new_value):
    """This function is needed to flag_modify the particular dictionary
    in case we mutate an internal dict, we could use a oneliner flag_modified but 
    it's more intuitive to explicitly do this and take advantage of `MutableDict`

    Args:
        obj: The class property  which is a dictionary
        dictionary_key (str)
        internal_key (str)
        new_value (Any)
    """
    key = obj[dictionary_key]
    key[internal_key] = new_value
    obj[dictionary_key] = key


# pylint: enable=E1101


def clean_node(a: _U):
    x = a.as_json
    x.pop("_secure_")
    return x
