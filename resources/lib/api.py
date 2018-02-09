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

import xbmc


class API:
    """Api documentation
    https://github.com/CloudMax94/crunchyroll-api/wiki/Api
    """
    URL    = "https://api.crunchyroll.com/"
    VERSON = "1.1.21.0"
    TOKEN  = "LNDJgOit5yaRIWN"
    DEVICE = "com.crunchyroll.windows.desktop"


def start(args):
    """Login and session handler
    """
    # create cookiejar
    args._cj = LWPCookieJar()

    # lets urllib handle cookies
    opener = build_opener(HTTPCookieProcessor(args._cj))
    opener.addheaders = [("User-Agent",      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Edge/16.16299"),
                         ("Accept-Encoding", "identity"),
                         ("Accept",          "*/*"),
                         ("Content-Type",    "application/x-www-form-urlencoded")]
    install_opener(opener)

    # load cookies
    try:
        args._cj.load(getCookiePath(args), ignore_discard=True)
    except IOError:
        # cookie file does not exist
        pass

    # get login informations
    username = args._addon.getSetting("crunchyroll_username")
    password = args._addon.getSetting("crunchyroll_password")

    # session management
    if not (args._session_id and args._auth_token):
        # create new session
        payload = {"device_id":    args._device_id,
                   "device_type":  API.DEVICE,
                   "access_token": API.TOKEN}
        req = request(args, "start_session", payload, True)

        # check for error
        if req["error"]:
            return False
        args._session_id = req["data"]["session_id"]

        # make login
        payload = {"password": password,
                   "account":  username}
        req = request(args, "login", payload, True)

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
        req = request(args, "start_session", payload, True)

        # check for error
        if req["error"]:
            destroy(args)
            return False
        args._session_id = req["data"]["session_id"]
        args._auth_token = req["data"]["auth"]
        args._session_restart = False

    return True


def close(args):
    """Saves cookies and session
    """
    args._addon.setSetting("session_id", args._session_id)
    args._addon.setSetting("auth_token", args._auth_token)
    if args._cj:
        args._cj.save(getCookiePath(args), ignore_discard=True)


def destroy(args):
    """Destroys session
    """
    args._addon.setSetting("session_id", "")
    args._addon.setSetting("auth_token", "")
    remove(getCookiePath(args))
    args._session_id = ""
    args._auth_token = ""
    args._cj = False


def request(args, method, options, failed=False):
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
        xbmc.log("[PLUGIN] %s: API returned error '%s'" % (args._addonname, str(json_data)), xbmc.LOGNOTICE)
        args._session_restart = True
        if not failed:
            # retry request, session expired
            start(args)
            return request(args, method, options, True)
        elif failed:
            # destroy session
            destroy(args)

    return json_data


def getCookiePath(args):
    """Get cookie file path
    """
    profile_path = xbmc.translatePath(args._addon.getAddonInfo("profile"))
    if args.PY2:
        return join(profile_path.decode("utf-8"), u"cookies.lwp")
    else:
        return join(profile_path, "cookies.lwp")
