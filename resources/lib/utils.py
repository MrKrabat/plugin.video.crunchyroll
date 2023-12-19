# -*- coding: utf-8 -*-
# Crunchyroll
# Copyright (C) 2018 MrKrabat
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from requests import Response
import re
import xbmc
from json import dumps

try:
    from urlparse import parse_qs
    from urllib import unquote_plus
except ImportError:
    from urllib.parse import parse_qs, unquote_plus

from datetime import datetime
import time
from typing import Dict, Optional

from .model import Args, LoginError, CrunchyrollError


def parse(argv):
    """Decode arguments
    """
    if argv[2]:
        return Args(argv, parse_qs(argv[2][1:]))
    else:
        return Args(argv, {})


def headers() -> Dict:
    return {
        "User-Agent": "Crunchyroll/3.10.0 Android/6.0 okhttp/4.9.1",
        "Content-Type": "application/x-www-form-urlencoded"
    }


def get_date() -> datetime:
    return datetime.utcnow()


def date_to_str(date: datetime) -> str:
    return "{}-{}-{}T{}:{}:{}Z".format(
        date.year, date.month,
        date.day, date.hour,
        date.minute, date.second
    )


def str_to_date(string: str) -> datetime:
    time_format = "%Y-%m-%dT%H:%M:%SZ"

    try:
        res = datetime.strptime(string, time_format)
    except TypeError:
        res = datetime(*(time.strptime(string, time_format)[0:6]))

    return res


def get_json_from_response(r: Response) -> Optional[Dict]:
    code: int = r.status_code
    try:
        r_json: Dict = r.json()
    except ValueError:
        # no data, possibly a POST to playheads?
        return {}

    if "error" in r_json:
        error_code = r_json.get("error")
        if error_code == "invalid_grant":
            raise LoginError(f"[{code}] Invalid login credentials.")
    elif "message" in r_json and "code" in r_json:
        message = r_json.get("message")
        raise CrunchyrollError(f"[{code}] Error occurred: {message}")
    if code != 200:
        raise CrunchyrollError(f"[{code}] {r.text}")

    return r_json


def get_stream_id_from_url(url: str):
    stream_id = re.search('/videos/([^/]+)/streams', url)
    if stream_id is None:
        return None

    return stream_id[1]


def get_watched_status_from_playheads_data(playheads_data, episode_id) -> int:
    if playheads_data and playheads_data["data"]:
        for info in playheads_data["data"]:
            if info["content_id"] == episode_id:
                return 1 if (info["fully_watched"] is True) else 0

    return 0


def dump(data):
    xbmc.log(dumps(data, indent=4), xbmc.LOGINFO)
