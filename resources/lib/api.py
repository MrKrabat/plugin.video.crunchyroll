# -*- coding: utf-8 -*-
# Crunchyroll
# based on work by stefanodvx
# Copyright (C) 2023 smirgol
#
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

import json
import time
from datetime import timedelta, datetime
from typing import Optional, Dict

import requests
import xbmc
import xbmcvfs
from requests import HTTPError, Response

from . import utils
from .model import AccountData, Args, LoginError


class API:
    """Api documentation
    https://github.com/CloudMax94/crunchyroll-api/wiki/Api
    """
    # URL = "https://api.crunchyroll.com/"
    # VERSION = "1.1.21.0"
    # TOKEN = "LNDJgOit5yaRIWN"
    # DEVICE = "com.crunchyroll.windows.desktop"
    # TIMEOUT = 30

    INDEX_ENDPOINT = "https://beta-api.crunchyroll.com/index/v2"
    PROFILE_ENDPOINT = "https://beta-api.crunchyroll.com/accounts/v1/me/profile"
    TOKEN_ENDPOINT = "https://beta-api.crunchyroll.com/auth/v1/token"
    SEARCH_ENDPOINT = "https://beta-api.crunchyroll.com/content/v1/search"
    STREAMS_ENDPOINT = "https://beta-api.crunchyroll.com/cms/v2{}/videos/{}/streams"
    # SERIES_ENDPOINT = "https://beta-api.crunchyroll.com/cms/v2{}/series/{}"
    SEASONS_ENDPOINT = "https://beta-api.crunchyroll.com/cms/v2{}/seasons"
    EPISODES_ENDPOINT = "https://beta-api.crunchyroll.com/cms/v2{}/episodes"
    OBJECTS_BY_ID_LIST_ENDPOINT = "https://beta-api.crunchyroll.com/content/v2/cms/objects/{}"
    # SIMILAR_ENDPOINT = "https://beta-api.crunchyroll.com/content/v1/{}/similar_to"
    # NEWSFEED_ENDPOINT = "https://beta-api.crunchyroll.com/content/v1/news_feed"
    BROWSE_ENDPOINT = "https://beta-api.crunchyroll.com/content/v1/browse"
    # there is also a v2, but that will only deliver content_ids and no details about the entries
    WATCHLIST_LIST_ENDPOINT = "https://beta-api.crunchyroll.com/content/v1/{}/watchlist"
    # only v2 will allow removal of watchlist entries.
    # !!!! be super careful and always provide a content_id, or it will delete the whole playlist! *sighs* !!!!
    # WATCHLIST_REMOVE_ENDPOINT = "https://beta-api.crunchyroll.com/content/v2/{}/watchlist/{}"
    WATCHLIST_V2_ENDPOINT = "https://beta-api.crunchyroll.com/content/v2/{}/watchlist"
    PLAYHEADS_ENDPOINT = "https://beta-api.crunchyroll.com/content/v2/{}/playheads"
    HISTORY_ENDPOINT = "https://beta-api.crunchyroll.com/content/v2/{}/watch-history"
    RESUME_ENDPOINT = "https://beta-api.crunchyroll.com/content/v2/discover/{}/history"
    SEASONAL_TAGS_ENDPOINT = "https://beta-api.crunchyroll.com/content/v2/discover/seasonal_tags"
    CATEGORIES_ENDPOINT = "https://beta-api.crunchyroll.com/content/v1/tenant_categories"
    SKIP_EVENTS_ENDPOINT = "https://static.crunchyroll.com/skip-events/production/{}.json"  # request w/o auth req.
    INTRO_V2_ENDPOINT = "https://static.crunchyroll.com/datalab-intro-v2/{}.json"

    CRUNCHYLISTS_LISTS_ENDPOINT = "https://beta-api.crunchyroll.com/content/v2/{}/custom-lists"
    CRUNCHYLISTS_VIEW_ENDPOINT = "https://beta-api.crunchyroll.com/content/v2/{}/custom-lists/{}"

    AUTHORIZATION = "Basic bHF0ai11YmY1aHF4dGdvc2ZsYXQ6N2JIY3hfYnI0czJubWE1bVdrdHdKZEY0ZTU2UU5neFQ="

    def __init__(
            self,
            args: Args = None,
            locale: str = "en-US"
    ) -> None:
        self.http = requests.Session()
        self.locale: str = locale
        self.account_data: AccountData = AccountData(dict())
        self.api_headers: Dict = default_request_headers()
        self.args = args
        self.retry_counter = 0

    def start(self) -> bool:
        session_restart = self.args.get_arg('session_restart', False)

        # restore account data from file
        session_data = self.load_from_storage()
        if session_data and not session_restart:
            self.account_data = AccountData(session_data)
            account_auth = {"Authorization": f"{self.account_data.token_type} {self.account_data.access_token}"}
            self.api_headers.update(account_auth)

            # check if tokes are expired
            if get_date() > str_to_date(self.account_data.expires):
                session_restart = True
            else:
                return True

        # session management
        self.create_session(session_restart)

        return True

    def create_session(self, refresh=False) -> None:
        # get login information
        username = self.args.addon.getSetting("crunchyroll_username")
        password = self.args.addon.getSetting("crunchyroll_password")

        headers = {"Authorization": API.AUTHORIZATION}
        data = {}

        if not refresh:
            data = {
                "username": username,
                "password": password,
                "grant_type": "password",
                "scope": "offline_access",
            }
        elif refresh:
            data = {
                "refresh_token": self.account_data.refresh_token,
                "grant_type": "refresh_token",
                "scope": "offline_access",
            }

        r = self.http.request(
            method="POST",
            url=API.TOKEN_ENDPOINT,
            headers=headers,
            data=data
        )

        # if refreshing and refresh token is expired, it will throw a 400
        # retry with a fresh login, but limit retries to prevent loop in case something else went wrong
        if r.status_code == 400:
            utils.crunchy_log(self.args, "Invalid/Expired credentials, restarting session from scratch")
            self.retry_counter = self.retry_counter + 1
            self.delete_storage()
            if self.retry_counter > 2:
                utils.crunchy_log(self.args, "Max retries exceeded. Aborting!", xbmc.LOGERROR)
                raise LoginError("Failed to authenticate twice")
            return self.create_session()

        r_json = get_json_from_response(r)

        self.api_headers.clear()
        self.account_data = AccountData({})

        access_token = r_json["access_token"]
        token_type = r_json["token_type"]
        account_auth = {"Authorization": f"{token_type} {access_token}"}

        account_data = dict()
        account_data.update(r_json)
        self.account_data = AccountData({})
        self.api_headers.update(account_auth)

        r = self.make_request(
            method="GET",
            url=API.INDEX_ENDPOINT
        )
        account_data.update(r)

        r = self.make_request(
            method="GET",
            url=API.PROFILE_ENDPOINT
        )
        account_data.update(r)

        account_data["expires"] = date_to_str(
            get_date() + timedelta(seconds=float(account_data["expires_in"])))
        self.account_data = AccountData(account_data)

        self.write_to_storage(self.account_data)
        self.retry_counter = 0

    def close(self) -> None:
        """Saves cookies and session
        """
        # no longer required, data is saved upon session update already

    def destroy(self) -> None:
        """Destroys session
        """
        self.delete_storage()

    def make_request(
            self,
            method: str,
            url: str,
            headers=None,
            params=None,
            data=None,
            json_data=None,
            is_retry=False
    ) -> Optional[Dict]:
        if params is None:
            params = dict()
        if headers is None:
            headers = dict()
        if self.account_data:
            if expiration := self.account_data.expires:
                current_time = get_date()
                if current_time > str_to_date(expiration):
                    self.create_session(refresh=True)
            params.update({
                "Policy": self.account_data.cms.policy,
                "Signature": self.account_data.cms.signature,
                "Key-Pair-Id": self.account_data.cms.key_pair_id
            })
        request_headers = {}
        request_headers.update(self.api_headers)
        request_headers.update(headers)

        r = self.http.request(
            method,
            url,
            headers=request_headers,
            params=params,
            data=data,
            json=json_data
        )

        # something went wrong with authentication, possibly an expired token that wasn't caught above due to host
        # clock issues. set expiration date to 0 and re-call, triggering a full session refresh.
        if r.status_code == 401:
            if is_retry:
                raise LoginError('Request to API failed twice due to authentication issues.')

            utils.crunchy_log(self.args, "make_request_proposal: request failed due to auth error", xbmc.LOGERROR)
            self.account_data.expires = 0
            return self.make_request(method, url, headers, params, data, json_data, True)

        return get_json_from_response(r)

    def make_unauthenticated_request(
            self,
            method: str,
            url: str,
            headers=None,
            params=None,
            data=None,
            json_data=None,
    ) -> Optional[Dict]:
        """ Send a raw request without any session information """

        req = requests.Request(method, url, data=data, params=params, headers=headers, json=json_data)
        prepped = req.prepare()
        r = self.http.send(prepped)

        return get_json_from_response(r)

    def get_storage_path(self) -> str:
        """Get cookie file path
        """
        profile_path = xbmcvfs.translatePath(self.args.addon.getAddonInfo("profile"))

        return profile_path

    def load_from_storage(self) -> Optional[Dict]:
        storage_file = self.get_storage_path() + "session_data.json"

        if not xbmcvfs.exists(storage_file):
            return None

        with xbmcvfs.File(storage_file) as file:
            data = json.load(file)

        d = dict()
        d.update(data)

        return d

    def delete_storage(self) -> None:
        storage_file = self.get_storage_path() + "session_data.json"

        if not xbmcvfs.exists(storage_file):
            return None

        xbmcvfs.delete(storage_file)

    def write_to_storage(self, account: AccountData) -> bool:
        storage_file = self.get_storage_path() + "session_data.json"

        # serialize (Object has a to_str serializer)
        json_string = str(account)

        with xbmcvfs.File(storage_file, 'w') as file:
            result = file.write(json_string)

        return result


def default_request_headers() -> Dict:
    return {
        "User-Agent": "Crunchyroll/3.50.2 Android/14 okhttp/4.12.0",
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
    from .utils import log_error_with_trace
    from .model import CrunchyrollError

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

    if not r.ok and r.text[0] != "{":
        raise CrunchyrollError(f"[{code}] {r.text}")

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
