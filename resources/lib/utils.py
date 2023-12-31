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

import re
from json import dumps

import requests
import xbmc
import xbmcgui
from requests import Response
from requests.exceptions import HTTPError

try:
    from urlparse import parse_qs
    from urllib import unquote_plus
except ImportError:
    from urllib.parse import parse_qs, unquote_plus

from datetime import datetime
import time
from typing import Dict, Optional, Union

from .model import Args, LoginError, CrunchyrollError


def parse(argv) -> Args:
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
    response_type: str = r.headers.get("Content-Type")

    # no content - possibly POST/DELETE request?
    if not r or not r.text:
        try:
            r.raise_for_status()
            return None
        except HTTPError as e:
            # r.text is empty when status code cause raise
            r = e.response

    # handle text/plain response (e.g. fetch subtitle)
    if response_type == "text/plain":
        # if encoding is not provided in the response, Requests will make an educated guess and very likely fail
        # messing encoding up - which did cost me hours. We will always receive utf-8 from crunchy, so enforce that
        r.encoding = "utf-8"
        d = dict()
        d.update({
            'data': r.text
        })
        return d

    try:
        r_json: Dict = r.json()
    except requests.exceptions.JSONDecodeError:
        log_error_with_trace(None, "Failed to parse response data")
        return None

    if "error" in r_json:
        error_code = r_json.get("error")
        if error_code == "invalid_grant":
            raise LoginError(f"[{code}] Invalid login credentials.")
    elif "message" in r_json and "code" in r_json:
        message = r_json.get("message")
        raise CrunchyrollError(f"[{code}] Error occurred: {message}")
    if not r.ok:
        raise CrunchyrollError(f"[{code}] {r.text}")

    return r_json


def get_series_data_from_series_ids(args, ids: list, api) -> dict:
    req = api.make_request(
        method="GET",
        url=api.OBJECTS_BY_ID_LIST_ENDPOINT.format(','.join(ids)),
        params={
            "locale": args.subtitle,
            # "preferred_audio_language": ""
        }
    )
    if not req or "error" in req:
        return {}

    return {item.get("id"): item for item in req.get("data")}


def get_stream_id_from_url(url: str) -> Union[str, None]:
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


def get_image_from_struct(item: Dict, image_type: str, depth: int = 2) -> Union[str, None]:
    if item.get("images") and item.get("images").get(image_type):
        src = item.get("images").get(image_type)
        for i in range(0, depth):
            if src[-1]:
                src = src[-1]
            else:
                return None
        if src.get('source'):
            return src.get('source')

    return None


def dump(data) -> None:
    xbmc.log(dumps(data, indent=4), xbmc.LOGINFO)


def log(message) -> None:
    xbmc.log(message, xbmc.LOGINFO)


def crunchy_log(args, message, loglevel=xbmc.LOGINFO) -> None:
    addon_name = args.addon_name if args is not None and hasattr(args, 'addon_name') else "Crunchyroll"
    xbmc.log("[PLUGIN] %s: %s" % (addon_name, str(message)), loglevel)


def log_error_with_trace(args, message, show_notification: bool = True) -> None:
    import sys
    import traceback

    # Get current system exception
    ex_type, ex_value, ex_traceback = sys.exc_info()

    # Extract unformatter stack traces as tuples
    trace_back = traceback.extract_tb(ex_traceback)

    # Format stacktrace
    stack_trace = list()

    for trace in trace_back:
        stack_trace.append(
            "File : %s , Line : %d, Func.Name : %s, Message : %s\n" % (trace[0], trace[1], trace[2], trace[3]))

    addon_name = args.addon_name if args is not None and hasattr(args, 'addon_name') else "Crunchyroll"

    xbmc.log("[PLUGIN] %s: %s" % (addon_name, str(message)), xbmc.LOGERROR)
    xbmc.log("[PLUGIN] %s: %s %s %s" % (addon_name, ex_type.__name__, ex_value, stack_trace), xbmc.LOGERROR)

    if show_notification:
        xbmcgui.Dialog().notification(
            '%s Error' % args.addonname,
            'Please check logs for details',
            xbmcgui.NOTIFICATION_ERROR,
            5
        )


def convert_subtitle_index_to_string(subtitle_index: int) -> str:
    if subtitle_index == "0":
        return "en-US"
    elif subtitle_index == "1":
        return "en-GB"
    elif subtitle_index == "2":
        return "es-419"
    elif subtitle_index == "3":
        return "es-ES"
    elif subtitle_index == "4":
        return "pt-BR"
    elif subtitle_index == "5":
        return "pt-PT"
    elif subtitle_index == "6":
        return "fr-FR"
    elif subtitle_index == "7":
        return "de-DE"
    elif subtitle_index == "8":
        return "ar-ME"
    elif subtitle_index == "9":
        return "it-IT"
    elif subtitle_index == "10":
        return "ru-RU"
    elif subtitle_index == "11":
        return ""
    else:
        return "en-US"


def convert_language_iso_to_string(args: Args, language_iso: str) -> str:
    if language_iso == "en-US":
        return args.addon.getLocalizedString(30021)
    elif language_iso == "en-GB":
        return args.addon.getLocalizedString(30022)
    elif language_iso == "es-419":
        return args.addon.getLocalizedString(30023)
    elif language_iso == "es-ES":
        return args.addon.getLocalizedString(30024)
    elif language_iso == "pt-BR":
        return args.addon.getLocalizedString(30025)
    elif language_iso == "pt-PT":
        return args.addon.getLocalizedString(30026)
    elif language_iso == "fr-FR":
        return args.addon.getLocalizedString(30027)
    elif language_iso == "de-DE":
        return args.addon.getLocalizedString(30028)
    elif language_iso == "ar-ME":
        return args.addon.getLocalizedString(30029)
    elif language_iso == "it-IT":
        return args.addon.getLocalizedString(30030)
    elif language_iso == "ru-RU":
        return args.addon.getLocalizedString(30031)
    else:
        return language_iso


def filter_series(args: Args, item: Dict) -> bool:
    # is it a dub in my main language?
    if args.subtitle == item.get('audio_locale', ""):
        return True

    # is it a dub in my alternate language?
    if args.subtitle_fallback and args.subtitle_fallback == item.get('audio_locale', ""):
        return True

    # is it japanese audio, but there are subtitles in my main language?
    if item.get("audio_locale") == "ja-JP":
        # fix for missing subtitles in data
        if item.get("subtitle_locales", []) == [] and item.get('is_subbed', False) is True:
            return True

        if args.subtitle in item.get("subtitle_locales", []):
            return True

        if args.subtitle_fallback and args.subtitle_fallback in item.get("subtitle_locales", []):
            return True

    return False


def format_long_episode_title(season_title: str, episode_number: str, title: str):
    return season_title + " #" + str(episode_number) + " - " + title


def format_short_episode_title(season_number: int, episode_number: str, title: str):
    return (str(season_number) + "x" if season_number else "") + two_digits(episode_number) + ". " + title


def two_digits(n):
    if not n:
        return "00"
    if n < 10:
        return "0" + str(n)
    return str(n)
