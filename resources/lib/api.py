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

import json
import xbmcvfs
from os import remove
from os.path import join
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode
try:
    from urllib2 import urlopen, build_opener, HTTPCookieProcessor, install_opener
except ImportError:
    from urllib.request import urlopen, build_opener, HTTPCookieProcessor, install_opener
try:
    from cookielib import LWPCookieJar
except ImportError:
    from http.cookiejar import LWPCookieJar

import requests
import re
from datetime import timedelta
from typing import Optional, List, Dict
from requests.models import Response
from . import model

import xbmc


class API:
    """Api documentation
    https://github.com/CloudMax94/crunchyroll-api/wiki/Api
    """
    URL    = "https://api.crunchyroll.com/"
    VERSON = "1.1.21.0"
    TOKEN  = "LNDJgOit5yaRIWN"
    DEVICE = "com.crunchyroll.windows.desktop"
    TIMEOUT = 30

    INDEX_ENDPOINT = "https://beta-api.crunchyroll.com/index/v2"
    PROFILE_ENDPOINT = "https://beta-api.crunchyroll.com/accounts/v1/me/profile"
    TOKEN_ENDPOINT = "https://beta-api.crunchyroll.com/auth/v1/token"
    SEARCH_ENDPOINT = "https://beta-api.crunchyroll.com/content/v1/search"
    STREAMS_ENDPOINT = "https://beta-api.crunchyroll.com/cms/v2{}/videos/{}/streams"
    SERIES_ENDPOINT = "https://beta-api.crunchyroll.com/cms/v2{}/series/{}"
    SEASONS_ENDPOINT = "https://beta-api.crunchyroll.com/cms/v2{}/seasons"
    EPISODES_ENDPOINT = "https://beta-api.crunchyroll.com/cms/v2{}/episodes"
    SIMILAR_ENDPOINT = "https://beta-api.crunchyroll.com/content/v1/{}/similar_to"
    NEWSFEED_ENDPOINT = "https://beta-api.crunchyroll.com/content/v1/news_feed"
    BROWSE_ENDPOINT = "https://beta-api.crunchyroll.com/content/v1/browse"
    WATCHLIST_LIST_ENDPOINT = "https://beta-api.crunchyroll.com/content/v1/{}/watchlist"
    WATCHLIST_SERIES_ENDPOINT = "https://beta-api.crunchyroll.com/content/v1/{}/watchlist/{}"
    PLAYHEADS_ENDPOINT = "https://www.crunchyroll.com/content/v2/{}/playheads"

    AUTHORIZATION = "Basic aHJobzlxM2F3dnNrMjJ1LXRzNWE6cHROOURteXRBU2Z6QjZvbXVsSzh6cUxzYTczVE1TY1k="

    def __init__(
        self,
        locale: str="en-US"
    ) -> None:
        self.http = requests.Session()
        self.locale: str = locale
        self.account_data: AccountData = AccountData(dict())
        self.api_headers: Dict = self.headers()

    def start(args):
        # get login informations
        username = args._addon.getSetting("crunchyroll_username")
        password = args._addon.getSetting("crunchyroll_password")
        session_restart = getattr(args, "_session_restart", False)

        # session management
        self.createSession(args, session_restart)

        return True

    def createSession(self, refresh=False):
        # get login informations
        username = self._addon.getSetting("crunchyroll_username")
        password = self._addon.getSetting("crunchyroll_password")

        headers = {"Authorization": API.AUTHORIZATION}

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
        r_json = self._get_json(r)

        self.api_headers.clear()
        self.account_data = AccountData({})

        access_token = r_json["access_token"]
        token_type = r_json["token_type"]
        account_auth = {"Authorization": f"{token_type} {access_token}"}

        account_data = dict()
        account_data.update(r_json)
        self.account_data = AccountData({})
        self.api_headers.update(account_auth)

        r = self._make_request(
            method="GET",
            url=API.INDEX_ENDPOINT
        )
        account_data.update(r)

        r = self._make_request(
            method="GET",
            url=API.PROFILE_ENDPOINT
        )
        account_data.update(r)

        account_data["expires"] = date_to_str(get_date() + timedelta(seconds=account_data["expires_in"]))
        self.account_data = AccountData(account_data)


    def close(args):
        # @TODO: update

        """Saves cookies and session
        """
        #args._addon.setSetting("session_id", args._session_id)
        #args._addon.setSetting("auth_token", args._auth_token)
        #if args._cj:
        #    args._cj.save(getCookiePath(args), ignore_discard=True)


    def destroy(args):
        # @TODO: update

        """Destroys session
        """
        #args._addon.setSetting("session_id", "")
        #args._addon.setSetting("auth_token", "")
        #args._session_id = ""
        #args._auth_token = ""
       # args._cj = False
       # try:
       #    remove(getCookiePath(args))
        #except WindowsError:
        #    pass

    # @DEPRECATED
    def request_old(args, method, options, failed=False):
        # @TODO: remove
        xbmc.log("[PLUGIN] %s: CALL TO DEPRECATED METHOD 'request' with for %s" % (args._addonname, method), xbmc.LOGINFO)

        """Make Crunchyroll JSON API call
        """
        # required in every request
        payload = {"version": API.VERSON,
                   "locale":  args._subtitle}

        # if not new session add access token
        if not method == "start_session":
            payload["session_id"] = args._session_id

        # merge payload with parameters
        payload.update(options)
        payload = urlencode(payload)

        # send payload
        url = API.URL + method + ".0.json"
        response = urlopen(url, payload.encode("utf-8"), API.TIMEOUT)

        # parse response
        json_data = response.read().decode("utf-8")
        json_data = json.loads(json_data)

        # check for error
        if json_data["error"]:
            xbmc.log("[PLUGIN] %s: API returned error '%s'" % (args._addonname, str(json_data)), xbmc.LOGINFO)
            args._session_restart = True
            if not failed:
                # retry request, session expired
                start(args)
                return request(args, method, options, True)
            elif failed:
                # destroy session
                destroy(args)

        return json_data

    def _make_request(
        self,
        method: str,
        url: str,
        headers: Dict=dict(),
        params: Dict=dict(),
        data=None
    ) -> Optional[Dict]:
        if self.account_data:
            if expiration := self.account_data.expires:
                current_time = self.get_date()
                if current_time > self.str_to_date(expiration):
                    self._create_session(refresh=True)
            params.update({
                "Policy": self.account_data.cms.policy,
                "Signature": self.account_data.cms.signature,
                "Key-Pair-Id": self.account_data.cms.key_pair_id
            })
        headers.update(self.api_headers)
        r = self.http.request(
            method,
            url,
            headers=headers,
            params=params,
            data=data
        )
        return self._get_json(r)

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
        return datetime.strptime(
            string,
            "%Y-%m-%dT%H:%M:%SZ"
        )

    def _get_json(self, r: Response) -> Optional[Dict]:
        # @TODO: better error handling
        code: int = r.status_code
        r_json: Dict = r.json()
        if "error" in r_json:
            error_code = r_json.get("error")
            if error_code == "invalid_grant":
                raise LoginError(f"[{code}] Invalid login credentials.")
        elif "message" in r_json and "code" in r_json:
            message = r_json.get("message")
            raise CrunchyrollError(f"[{code}] Error occured: {message}")
        if code != 200:
            raise CrunchyrollError(f"[{code}] {r.text}")
        return r_json