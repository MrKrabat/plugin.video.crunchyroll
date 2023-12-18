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
#from os import remove
#from os.path import join

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
from datetime import timedelta
from typing import Optional, Dict
from model import AccountData, Args
from . import utils

import xbmc


class API:
    """Api documentation
    https://github.com/CloudMax94/crunchyroll-api/wiki/Api
    """
    URL = "https://api.crunchyroll.com/"
    VERSION = "1.1.21.0"
    TOKEN = "LNDJgOit5yaRIWN"
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
            args: Args = None,
            locale: str = "en-US"
    ) -> None:
        self.http = requests.Session()
        self.locale: str = locale
        self.account_data: AccountData = AccountData(dict())
        self.api_headers: Dict = utils.headers()
        self.args = args

    def start(self) -> bool:
        session_restart = getattr(self.args, "_session_restart", False)

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
        r_json = utils.get_json_from_response(r)

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

        account_data["expires"] = utils.date_to_str(utils.get_date() + timedelta(seconds=float(account_data["expires_in"])))
        self.account_data = AccountData(account_data)

    def close(self):
        # @TODO: update

        """Saves cookies and session
        """
        # self._addon.setSetting("session_id", self._session_id)
        # self._addon.setSetting("auth_token", self._auth_token)
        # if self._cj:
        #    self._cj.save(getCookiePath(args), ignore_discard=True)

    def destroy(self):
        # @TODO: update

        """Destroys session
        """
        # self._addon.setSetting("session_id", "")
        # self._addon.setSetting("auth_token", "")
        # self._session_id = ""
        # self._auth_token = ""
        #
        # self._cj = False
        # try:
        #    remove(getCookiePath(self))
        # except WindowsError:
        #    pass

    # @DEPRECATED
    # def request_old(self, method, options, failed=False):
    #     # @TODO: remove
    #     xbmc.log("[PLUGIN] %s: CALL TO DEPRECATED METHOD 'request' with for %s" % (self._addonname, method),
    #              xbmc.LOGINFO)
    #
    #     """Make Crunchyroll JSON API call
    #     """
    #     # required in every request
    #     payload = {"version": API.VERSION,
    #                "locale": self._subtitle}
    #
    #     # if not new session add access token
    #     if not method == "start_session":
    #         payload["session_id"] = self._session_id
    #
    #     # merge payload with parameters
    #     payload.update(options)
    #     payload = urlencode(payload)
    #
    #     # send payload
    #     url = API.URL + method + ".0.json"
    #     response = urlopen(url, payload.encode("utf-8"), API.TIMEOUT)
    #
    #     # parse response
    #     json_data = response.read().decode("utf-8")
    #     json_data = json.loads(json_data)
    #
    #     # check for error
    #     if json_data["error"]:
    #         xbmc.log("[PLUGIN] %s: API returned error '%s'" % (self._addonname, str(json_data)), xbmc.LOGINFO)
    #         self._session_restart = True
    #         if not failed:
    #             # retry request, session expired
    #             start(self)
    #             return request(self, method, options, True)
    #         elif failed:
    #             # destroy session
    #             destroy(self)
    #
    #     return json_data

    def make_request(
            self,
            method: str,
            url: str,
            headers=None,
            params=None,
            data=None
    ) -> Optional[Dict]:
        if params is None:
            params = dict()
        if headers is None:
            headers = dict()
        if self.account_data:
            if expiration := self.account_data.expires:
                current_time = utils.get_date()
                if current_time > utils.str_to_date(expiration):
                    self.create_session(refresh=True)
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
        return utils.get_json_from_response(r)
