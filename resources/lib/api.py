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

import time
from datetime import timedelta, datetime
from typing import Optional, Dict

import requests
import xbmc
from requests import HTTPError, Response

from . import utils
from .model import AccountData, Args, LoginError, ProfileData
from ..modules import cloudscraper


class API:
    """Api documentation
    https://github.com/CloudMax94/crunchyroll-api/wiki/Api
    """
    # URL = "https://api.crunchyroll.com/"
    # VERSION = "1.1.21.0"
    # TOKEN = "LNDJgOit5yaRIWN"
    # DEVICE = "com.crunchyroll.windows.desktop"
    # TIMEOUT = 30

    CRUNCHYROLL_UA = "Crunchyroll/3.54.0 Android/14 okhttp/4.12.0"

    INDEX_ENDPOINT = "https://beta-api.crunchyroll.com/index/v2"
    PROFILE_ENDPOINT = "https://beta-api.crunchyroll.com/accounts/v1/me/profile"
    TOKEN_ENDPOINT = "https://beta-api.crunchyroll.com/auth/v1/token"
    SEARCH_ENDPOINT = "https://beta-api.crunchyroll.com/content/v1/search"
    STREAMS_ENDPOINT = "https://beta-api.crunchyroll.com/cms/v2{}/videos/{}/streams"
    STREAMS_ENDPOINT_DRM = "https://cr-play-service.prd.crunchyrollsvc.com/v1/{}/android/phone/play"
    STREAMS_ENDPOINT_CLEAR_STREAM = "https://cr-play-service.prd.crunchyrollsvc.com/v1/token/{}/{}"
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

    AUTHORIZATION = "Basic bm12anNoZmtueW14eGtnN2ZiaDk6WllJVnJCV1VQYmNYRHRiRDIyVlNMYTZiNFdRb3Mzelg="
    LICENSE_ENDPOINT = "https://cr-license-proxy.prd.crunchyrollsvc.com/v1/license/widevine"

    PROFILES_LIST_ENDPOINT = "https://beta-api.crunchyroll.com/accounts/v1/me/multiprofile"
    STATIC_IMG_PROFILE = "https://static.crunchyroll.com/assets/avatar/170x170/"
    STATIC_WALLPAPER_PROFILE = "https://static.crunchyroll.com/assets/wallpaper/720x180/"

    def __init__(
            self,
            args: Args = None,
            locale: str = "en-US"
    ) -> None:
        self.http = requests.Session()
        self.locale: str = locale
        self.account_data: AccountData = AccountData(dict(), args)
        self.profile_data: ProfileData = ProfileData(dict(), args)
        self.api_headers: Dict = default_request_headers()
        self.args = args
        self.retry_counter = 0

    def start(self) -> None:
        session_restart = self.args.get_arg('session_restart', False)
        # 1 = Success, 0 = Failure, 2 = Success, first login
        returned = 1

        # restore account data from file (if any)
        account_data = self.account_data.load_from_storage()

        # restore profile data from file (if any)
        self.profile_data = ProfileData(self.profile_data.load_from_storage(), self.args)

        if account_data and not session_restart:
            self.account_data = AccountData(account_data, self.args)
            account_auth = {"Authorization": f"{self.account_data.token_type} {self.account_data.access_token}"}
            self.api_headers.update(account_auth)

            # check if tokes are expired
            if get_date() > str_to_date(self.account_data.expires):
                session_restart = True
            else:
                return

        # session management
        self.create_session(action="refresh" if session_restart else "access")

    def create_session(self, action: str = "login", profile_id: Optional[str] = None) -> None:
        # get login information
        username = self.args.addon.getSetting("crunchyroll_username")
        password = self.args.addon.getSetting("crunchyroll_password")

        headers = {"Authorization": API.AUTHORIZATION}
        data = {}

        if action == "login":
            data = {
                "username": username,
                "password": password,
                "grant_type": "password",
                "scope": "offline_access",
                "device_id": self.args.device_id,
                "device_name": 'Kodi',
                "device_type": 'MediaCenter'
            }
        elif action == "refresh":
            data = {
                "refresh_token": self.account_data.refresh_token,
                "grant_type": "refresh_token",
                "scope": "offline_access",
                "device_id": self.args.device_id,
                "device_name": 'Kodi',
                "device_type": 'MediaCenter'
            }
        elif action == "refresh_profile":
            data = {
                "device_id": self.args.device_id,
                "device_name": 'Kodi',
                "device_type": "MediaCenter",
                "grant_type": "refresh_token_profile_id",
                "profile_id": profile_id,
                "refresh_token": self.account_data.refresh_token
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
            self.account_data.delete_storage()
            if self.retry_counter > 2:
                utils.crunchy_log(self.args, "Max retries exceeded. Aborting!", xbmc.LOGERROR)
                raise LoginError("Failed to authenticate twice")
            return self.create_session()

        if r.status_code == 403:
            utils.crunchy_log(self.args, "Possible cloudflare shenanigans")
            scraper = cloudscraper.create_scraper(delay=10, browser={'custom': self.CRUNCHYROLL_UA})
            r = scraper.post(
                url=API.TOKEN_ENDPOINT,
                headers=headers,
                data=data
            )

            if 'access_token' not in r.text:
                raise LoginError("Failed to bypass cloudflare")

        r_json = get_json_from_response(r)

        self.api_headers.clear()
        self.account_data = AccountData({}, self.args)

        access_token = r_json["access_token"]
        token_type = r_json["token_type"]
        account_auth = {"Authorization": f"{token_type} {access_token}"}

        account_data = dict()
        account_data.update(r_json)
        self.account_data = AccountData({}, self.args)
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

        if action == "refresh_profile":
            # fetch all profiles from API
            r = self.make_request(
                method="GET",
                url=self.PROFILES_LIST_ENDPOINT,
            )

            # Extract current profile data as dict from ProfileData obj
            profile_data = vars(self.profile_data)

            # Update extracted profile data with fresh data from API for requested profile_id
            profile_data.update(
                next(profile for profile in r.get("profiles") if profile["profile_id"] == profile_id)
            )

            # update our ProfileData obj with updated data
            self.profile_data = ProfileData(profile_data, self.args)

            # cache to file
            self.profile_data.write_to_storage()

        account_data["expires"] = date_to_str(
            get_date() + timedelta(seconds=float(account_data["expires_in"])))

        self.account_data = AccountData(account_data, self.args)
        self.account_data.write_to_storage()

        self.retry_counter = 0

    def close(self) -> None:
        """Saves cookies and session
        """
        # no longer required, data is saved upon session update already

    def destroy(self) -> None:
        """Destroys session
        """
        self.account_data.delete_storage()
        self.profile_data.delete_storage()

    def make_request(
            self,
            method: str,
            url: str,
            headers=None,
            params=None,
            data=None,
            json_data=None,
            is_retry=False,
    ) -> Optional[Dict]:
        if params is None:
            params = dict()
        if headers is None:
            headers = dict()
        if self.account_data:
            if expiration := self.account_data.expires:
                current_time = get_date()
                if current_time > str_to_date(expiration):
                    self.create_session(action="refresh")
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


def default_request_headers() -> Dict:
    return {
        "User-Agent": API.CRUNCHYROLL_UA,
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
