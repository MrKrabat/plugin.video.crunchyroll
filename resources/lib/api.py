# -*- coding: utf-8 -*-
# Crunchyroll
# Copyright (C) 2017 MrKrabat
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

import os
import json
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

import xbmc


class API:
    """Api documentation
    https://github.com/CloudMax94/crunchyroll-api/wiki/Api
    """
    URL    = "https://api.crunchyroll.com/"
    VERSON = "2313.8"
    TOKEN  = "QWjz212GspMHH9h"
    DEVICE = "com.crunchyroll.iphone"


def start(username, password, args):
    """Login and session handler
    """
    # create cookie path
    cookiepath = os.path.join(
        xbmc.translatePath(args._addon.getAddonInfo("profile")),
        "cookies.lwp")

    # create cookiejar
    cj = LWPCookieJar()
    args._cj = cj

    # lets urllib2 handle cookies
    opener = build_opener(HTTPCookieProcessor(cj))
    opener.addheaders = [("User-Agent",      "Mozilla/5.0 (iPhone; iPhone OS 8.3.0; en_US)"),
                         ("Accept-Encoding", "identity"),
                         ("Accept",          "*/*"),
                         ("Content-Type",    "application/x-www-form-urlencoded")]
    install_opener(opener)

    # check if cookies exist
    try:
        cj.load(cookiepath, ignore_discard=True)
    except IOError:
        # cookie file does not exist
        pass

    # session management
    if not (args._session_id and args._auth_token):
        # create new session
        payload = {"device_id":    args._device_id,
                   "device_type":  API.DEVICE,
                   "access_token": API.TOKEN}
        req = request(args, "start_session", payload)

        # check for error
        if req["error"]:
            return False
        args._session_id = req["data"]["session_id"]

        # make login
        payload = {"password": password,
                   "account":  username}
        req = request(args, "login", payload)

        # check for error
        if req["error"]:
            return False
        args._auth_token = req["data"]["auth"]
    if not getattr(args, "_session_restart", False):
        pass
    else:
        # restart session
        payload = {"device_id":    args._device_id,
                   "device_type":  API.DEVICE,
                   "access_token": API.TOKEN,
                   "auth":         args._auth_token}
        req = request(args, "start_session", payload)

        # check for error
        if req["error"]:
            args._addon.setSetting("session_id", "")
            args._addon.setSetting("auth_token", "")
            args._session_id = ""
            args._auth_token = ""
            return False
        args._session_id = req["data"]["session_id"]
        args._auth_token = req["data"]["auth"]
        args._session_restart = False

    return True


def close(args):
    """Saves cookies and session
    """
    # create cookie path
    cookiepath = os.path.join(
        xbmc.translatePath(args._addon.getAddonInfo("profile")),
        "cookies.lwp")

    # save cookies
    args._cj.save(cookiepath, ignore_discard=True)
    args._addon.setSetting("session_id", args._session_id)
    args._addon.setSetting("auth_token", args._auth_token)


def request(args, method, options):
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
    response = urlopen(url, payload.encode("utf-8"))

    # parse response
    json_data = response.read().decode("utf-8")
    json_data = json.loads(json_data)

    # check for error
    if json_data["error"]:
        xbmc.log("[PLUGIN] %s: API returned error '%s'" % (args._addonname, str(req)), xbmc.LOGERROR)
        args._session_restart = True

    return json_data
