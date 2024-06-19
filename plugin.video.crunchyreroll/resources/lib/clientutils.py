# -*- coding: utf-8 -*-
# ${LICENSE_HEADER}

import xbmcaddon
from .utils import ADDON_ID, local_from_id
from .client import CrunchyrollClient


def init_crunchyroll_client():
    addon = xbmcaddon.Addon(id=ADDON_ID)
    email = addon.getSetting("crunchyroll_username")
    password = addon.getSetting("crunchyroll_password")
    prefered_audio = "original"
    if addon.getSettingInt("prefered_audio") != 0:
        prefered_audio = local_from_id(addon.getSettingInt("prefered_audio")-1)
    settings = {
        "prefered_subtitle": local_from_id(addon.getSettingInt("subtitle_language")),
        "prefered_audio": prefered_audio,
        "page_size": addon.getSettingInt("page_size"),
    }
    return CrunchyrollClient(email, password, settings)
