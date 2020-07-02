# ==================================================
#                  Utility Functions
# ==================================================
from email.utils import parseaddr as _parseaddr
from functools import wraps as _wraps
from json import dumps as _dumps
from pathlib import Path
from re import compile as _compile
from time import time as _time
from traceback import print_exc as _print_exc

from flask import Request as _Request
from flask import Response as _Response


# wraps list() around a map call
def map_to_list(*args) -> list:
    return list(map(*args))


# maybe only strip whitespace?
_sub = _compile(r"([^\w]|_)").sub
sanitize = lambda x: _sub("", x).strip().lower()

# js time in ms
js_time = lambda: _time() * 1e3


def get_origin(request: _Request) -> str:
    """
    for CORS requests
    On client we will send the x-qbytic-origin header
    or a query string to specify the origin

    Args:
        request (_Request): Flask request object

    Returns:
        str: the origin value 
    """
    get = request.headers.get
    return get("Origin") or get("x-qbytic-origin") or "*"


def validate_email_address(email_id: str) -> str:
    if "@" in _parseaddr(email_id)[1]:
        return email_id
    raise AppException("Invalid Email")


def safe_mkdir(dir_name: str):
    Path(dir_name).mkdir(exist_ok=True)


def safe_remove(filename: str):
    try:
        Path(filename).unlink()
    except:
        pass


class ParsedRequest:
    def __init__(self, request):
        self.args = dict(request.args)
        self.headers = request.headers
        self.json: dict = (request.get_json() or {})
        self.method = request.method


def json_response(data: dict, status=200, headers=None) -> _Response:
    dump = _dumps(data)
    resp = _Response(
        dump, status=status, headers=headers, content_type="application/json"
    )
    return resp


def api_response(func):
    # this has to be done otherwise flask will perceive all view_functions as `run`
    @_wraps(func)
    def run(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
            if isinstance(ret, _Response):
                return ret
            return json_response({"data": ret})

        except AppException as e:
            return json_response({"error": f"{e}"})
        except Exception as e:
            _print_exc()
            err = "An unknown error occured"
            return json_response({"error": err, "tb": f"{e}"})

    return run


class AppException(Exception):
    pass
