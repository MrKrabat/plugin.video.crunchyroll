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
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import os
from datetime import datetime
import xbmc
import xbmcvfs
import xbmcaddon
import requests
from .client import CrunchyrollClient

ADDON_ID = "plugin.video.crunchyreroll"
# The idea is to be able mock it for future tests
CRUNCHYROLL_API_URL = "https://beta-api.crunchyroll.com"
CRUNCHYROLL_STATIC_URL = "https://static.crunchyroll.com"
CRUNCHYROLL_PLAY_URL = "https://cr-play-service.prd.crunchyrollsvc.com"
CRUNCHYROLL_LICENSE_URL = "https://cr-license-proxy.prd.crunchyrollsvc.com/v1/license/widevine"
CRUNCHYROLL_UA = "Crunchyroll/3.50.1 Android/14 okhttp/4.12.0"


def local_from_id(locale_id):
    locales = [
        "en-US",
        "en-GB",
        "es-419",
        "es-ES",
        "pt-BR",
        "pt-PT",
        "fr-FR",
        "de-DE",
        "ar-SA",
        "it-IT",
        "ru-RU",
        "ta-IN",
        "hi-IN",
        "id-ID"
        "ms-MY",
        "th-TH",
        "vi-VN"
    ]

    if locale_id < len(locales):
        return locales[locale_id]

    return "en-US"


def lookup_playhead(playheads, content_id):
    for playhead in playheads:
        if playhead['content_id'] == content_id:
            return playhead

    return {"playhead": 0, "content_id": content_id, "fully_watched": False}


def lookup_episode(episodes, episode_id):
    for episode in episodes:
        if episode['id'] == episode_id:
            return episode
    return None


def lookup_stream_id(episode, prefered_audio_id):
    stream_id = None
    if "versions" in episode['episode_metadata'] and episode['episode_metadata']['versions']:
        if prefered_audio_id == 0:
            for version in episode['episode_metadata']['versions']:
                if version['original']:
                    stream_id = version['guid']
        else:
            prefered_audio = local_from_id(prefered_audio_id - 1)
            # If we find prefered_audio, it's return
            for version in episode['episode_metadata']['versions']:
                if version['audio_locale'] == prefered_audio:
                    stream_id = version['guid']
            # Else, we provide original version
            for version in episode['episode_metadata']['versions']:
                if version['original']:
                    stream_id = version['guid']
    else:
        stream_id = episode['id']
    return stream_id


def download_subtitle(url, output):
    with open(output, "w", encoding="utf8") as fh:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        response.encoding = "UTF-8"
        fh.write(response.text)
        fh.close()


def get_subtitles(episode_id, subtitles):
    cache_folder = xbmcvfs.translatePath("special://temp/crunchyroll_cache_subtitles")
    if not xbmcvfs.exists(cache_folder):
        xbmcvfs.mkdirs(cache_folder)

    return_subtitles = []
    for sub in list(subtitles.values()):
        lang = sub['language'].split('-')[0]
        # We keep sub['language'] in the name as we might have for the same lang many different language
        filename = f"{episode_id}.{sub['language']}.{lang}.{sub['format']}"
        file_path = xbmcvfs.translatePath(f"{cache_folder}/{filename}")

        if not xbmcvfs.exists(file_path):
            download_subtitle(sub['url'], file_path)
        else:
            now = datetime.timestamp(datetime.now())
            seven_days = 7 * 86400
            if xbmcvfs.Stat(file_path).st_ctime() > (now + seven_days):
                os.remove(xbmc.validatePath(file_path))
                download_subtitle(sub['url'], file_path)

        return_subtitles.append(file_path)
    return return_subtitles


def init_crunchyroll_client():
    addon = xbmcaddon.Addon(id=ADDON_ID)
    email = addon.getSetting("crunchyroll_username")
    password = addon.getSetting("crunchyroll_password")
    settings = {
        "prefered_subtitle": local_from_id(addon.getSettingInt("subtitle_language")),
        "prefered_audio": addon.getSettingInt("prefered_audio"),
        "page_size": addon.getSettingInt("page_size"),
        "resolution": int(addon.getSetting("resolution"))
    }
    return CrunchyrollClient(email, password, settings)


def sub_locale_from_id(locale_id):
    locales = [
        "eng",
        "eng",
        "spa",
        "spa",
        "por",
        "por",
        "fre",
        "ger",
        "ara",
        "ita",
        "rus",
        "tam",
        "hin",
        "ind",
        "may",
        "tha",
        "vie"
    ]
    if locale_id < len(locales):
        return locales[locale_id]

    return "eng"
