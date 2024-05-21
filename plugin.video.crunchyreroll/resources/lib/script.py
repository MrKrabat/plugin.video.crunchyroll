# -*- coding: utf-8 -*-
# Crunchyroll
# Copyright (C) 2024 Xtero
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>
import xbmc
import xbmcvfs
import xbmcaddon
from requests.models import PreparedRequest
from urlquick import Session, hash_url
from . import utils


def clear_subtitles_cache():
    cache_folder = xbmcvfs.translatePath(utils.get_cache_path())
    if xbmcvfs.exists(cache_folder):
        xbmc.log(f"[Crunchyroll] removing folder {cache_folder}")
        xbmcvfs.rmdir(cache_folder, True)  # pylint: disable=E1121
    xbmcvfs.mkdirs(cache_folder)


def clear_auth_cache():
    url = xbmcaddon.Addon(utils.ADDON_ID).getSetting("auth_url")
    s = Session()
    req = PreparedRequest()
    req.prepare(url=url, method="GET")

    hashed_url = hash_url(req)
    s.cache_adapter.del_cache(hashed_url)
