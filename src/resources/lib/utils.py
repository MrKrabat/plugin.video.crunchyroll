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

ADDON_ID="plugin.video.crunchyroll"

def local_from_id(id):
    subtitle = "en-US"
    if id == "0":
        subtitle = "en-US"
    elif id == "1":
        subtitle = "en-GB"
    elif id == "2":
        subtitle = "es-419"
    elif id == "3":
        subtitle = "es-ES"
    elif id == "4":
        subtitle = "pt-BR"
    elif id == "5":
        subtitle = "pt-PT"
    elif id == "6":
        subtitle = "fr-FR"
    elif id == "7":
        subtitle = "de-DE"
    elif id == "8":
        subtitle = "ar-ME"
    elif id == "9":
        subtitle = "it-IT"
    elif id == "10":
        subtitle = "ru-RU"

    return subtitle

def lookup_playhead(playheads, content_id):
    for playhead in playheads:
        if playhead['content_id'] == content_id:
            return playhead

    return { "playhead": 0, "content_id": content_id, "fully_watched": False }

def lookup_episode(episodes, id):
    for episode in episodes:
        if episode['id'] == id:
            return episode

def lookup_playlist_url(stream_list, locale):
    if locale in stream_list:
        return stream_list[locale]["url"]
    elif 'en-US' in stream_list:
        return stream_list["en-US"]["url"]
    else:
        return stream_list[""]["url"]

def lookup_stream_url(playlist, resolution):
    for item in playlist:
        if item.stream_info.resolution[1] == int(resolution):
            return item.uri
    return playlist[0].uri
