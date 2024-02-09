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

import re

ADDON_ID = "plugin.video.crunchyroll"
# The idea is to be able mock it for future tests
CRUNCHYROLL_API_URL = "https://beta-api.crunchyroll.com"
CRUNCHYROLL_STATIC_URL = "https://static.crunchyroll.com"
CRUNCHYROLL_PLAY_SERVICE = "https://cr-play-service.prd.crunchyrollsvc.com"
CRUNCHYROLL_UA = "Crunchyroll/3.48.3 Android/14 okhttp/4.12.0"


def local_from_id(locale_id):
    subtitle = "en-US"
    if locale_id == 0:
        subtitle = "en-US"
    elif locale_id == 1:
        subtitle = "en-GB"
    elif locale_id == 2:
        subtitle = "es-419"
    elif locale_id == 3:
        subtitle = "es-ES"
    elif locale_id == 4:
        subtitle = "pt-BR"
    elif locale_id == 5:
        subtitle = "pt-PT"
    elif locale_id == 6:
        subtitle = "fr-FR"
    elif locale_id == 7:
        subtitle = "de-DE"
    elif locale_id == 8:
        subtitle = "ar-ME"
    elif locale_id == 9:
        subtitle = "it-IT"
    elif locale_id == 10:
        subtitle = "ru-RU"

    return subtitle


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


def lookup_playlist_url(stream_list, locale):
    # pylint: disable=R1705
    if locale in stream_list:
        return stream_list[locale]["url"]
    elif 'en-US' in stream_list:
        return stream_list["en-US"]["url"]
    else:
        return stream_list[""]["url"]


def lookup_stream_url(playlist, resolution):
    for item in playlist:
        if item.stream_info.resolution[1] == resolution:
            return item.uri
    return playlist[0].uri


def lookup_stream_id(episode, prefered_audio_id):
    stream_id = None
    if "versions" in episode['episode_metadata'] and episode['episode_metadata']['versions']:
        if prefered_audio_id == 0:
            for version in episode['episode_metadata']['versions']:
                if version['original']:
                    stream_id = version['media_guid']
        else:
            prefered_audio = local_from_id(prefered_audio_id - 1)
            # If we find prefered_audio, it's return
            for version in episode['episode_metadata']['versions']:
                if version['audio_locale'] == prefered_audio:
                    stream_id = version['media_guid']
            # Else, we provide original version
            for version in episode['episode_metadata']['versions']:
                if version['original']:
                    stream_id = version['media_guid']
    else:
        stream_id = re.search(r"/content/v2/cms/videos/(\w+)/streams", episode['streams_link']).group(1)
    return stream_id


def lookup_subtitle(subtitles, prefered_subtitle):
    for sub in subtitles.values():
        if sub['language'] == prefered_subtitle:
            return sub['url']
    return None
