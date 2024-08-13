# -*- coding: utf-8 -*-
# ${LICENSE_HEADER}

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
