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

def lookup_for_audio_stream_id(args, data):
    # TODO manage prefered audio lang
    stream_id = None
    # Search for prefered audio stream
    for version in data['versions']:
        if version['audio_locale'] == "ja-JP":
            stream_id  = version['media_guid']
    # Fallback on VO
    if not stream_id:
        for version in data['versions']:
            if version['audio_locale'] == data["audio_locale"]:
                stream_id  = version['media_guid']
    return stream_id


# Info from panel class
def info_from_episode_panel_item(args, item):
    panel = item.get("panel",{})
    metadata = panel.get('episode_metadata',{})
    images = panel.get('images',[])
    infos = {
        "title":         metadata["series_title"] + " #" + str(metadata["episode_number"]) + " - " + panel["title"],
        "tvshowtitle":   metadata["series_title"],
        "duration":      int(metadata["duration_ms"]/1000),
        "playhead":      item['playhead'],
        "playcount":     0 if item["fully_watched"] else 1,
        "episode":       metadata["episode_number"],
        "stream_id":     lookup_for_audio_stream_id(args, metadata),
        "episode_id":    panel["id"],
        "collection_id": metadata["season_id"],
        "series_id":     metadata["series_id"],
        "plot":          panel["description"],
        "plotoutline":   panel["description"],
        "year":          metadata["episode_air_date"][:4],
        "aired":         metadata["episode_air_date"],
        "premiered":     metadata["availability_starts"],
        "thumb":         images["thumbnail"][0][0]["source"],
        "fanart":        images["thumbnail"][0][-1]["source"],
        "mode":          "videoplay"
    }
    return infos


# Info from episode class
def info_from_episode_item(args, item):
    images = item.get('images',[])
    infos = {
        "title":         item["series_title"] + " #" + str(item["episode_number"]) + " - " + item["title"],
        "tvshowtitle":   item["series_title"],
        "duration":      int(item["duration_ms"]/1000),
        "playcount":     0,
        "episode":       item["episode_number"],
        "stream_id":     lookup_for_audio_stream_id(args, item),
        "episode_id":    item["id"],
        "collection_id": item["season_id"],
        "series_id":     item["series_id"],
        "plot":          item["description"],
        "plotoutline":   item["description"],
        "year":          item["episode_air_date"][:4],
        "aired":         item["episode_air_date"],
        "premiered":     item["availability_starts"],
        "thumb":         images["thumbnail"][0][0]["source"],
        "fanart":        images["thumbnail"][0][-1]["source"],
        "mode":          "videoplay"
    }
    return infos


# Info from series class
def info_from_series_item(args, item):
    info = {
        "title":       item["title"],
        "tvshowtitle": item["title"],
        "series_id":   item["id"],
        "plot":        item["description"],
        "plotoutline": item["description"],
        "year":        item["series_metadata"]["series_launch_year"],
        "thumb":       item["images"]["poster_wide"][0][0]["source"],
        "fanart":      item["images"]["poster_wide"][0][-1]["source"],
        "mode":        "series"
    }
    return info


def info_from_season_item(args, item):
    pass


def local_from_id(id):
    subtitle = "en-US"
    if id == "0":
        subtitle = "en-US"
    elif id == "1":
        subtitle = "en-GB"
    elif id == "2":
        subtitle = "es-LA"
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
