# -*- coding: utf-8 -*-
# Crunchyroll
# Copyright (C) 2023 Xtero
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

# pylint: disable=E0401
import codequick


class Episode:

    def __init__(self, item, playhead):
        self.item = item
        self.playhead = playhead
        self.id = item["id"]
        self.number = item["episode_metadata"]["episode"] if item["episode_metadata"]["episode"] else "0"
        self.label = item["episode_metadata"]["series_title"] + " #" + self.number + " - " + item["title"]
        self.thumbnail = item["images"]["thumbnail"][0][0]["source"]
        self.landscape = item["images"]["thumbnail"][0][-1]["source"]
        self.duration = item["episode_metadata"]["duration_ms"] / 1000
        self.description = item["description"] if item["description"] else "no description"

    # Format info for codequick
    def to_dict(self):
        res = {
            "label": self.label,
            "art": {
                "thumb": self.thumbnail,
                "landscape": self.landscape,
                "fanart": self.landscape,
                "icon": self.thumbnail
            },
            "info": {
                "duration": self.duration,
                "plot": self.description,
                "episode": self.number,
                "tvshowtitle": self.item["episode_metadata"]["series_title"],
                "season": self.item["episode_metadata"]["season_number"],
                "originaltitle": self.id
            },
            "properties": {
                "totaltime": self.duration
            },
            "params": {
                "episode_id": self.id
            }
        }

        if "maturity_ratings" in self.item["episode_metadata"]:
            res["info"]["mpaa"] = self.item["episode_metadata"]["maturity_ratings"][0]

        if self.playhead["fully_watched"]:
            res["info"]["playcount"] = 1
        else:
            if int((self.playhead["playhead"] / self.duration) * 100) < 10:
                res["info"]["playcount"] = 0
            else:
                res["properties"]["resumetime"] = self.playhead["playhead"]

        return res


class Season:

    def __init__(self, item):
        self.item = item
        self.id = item["id"]
        self.label = item["title"]

    # Format info for codequick
    def to_dict(self):
        res = {
            "label": self.label,
            "params": {
                "season_id": self.id
            }

        }
        return res


class Series:

    def __init__(self, item):
        self.item = item
        self.id = item["id"]
        self.label = item["title"]
        self.thumbnail = item["images"]["poster_tall"][0][3]["source"]
        self.landscape = item["images"]["poster_wide"][0][-1]["source"]

    # Format info for codequick
    def to_dict(self):
        res = {
            "label": self.label,
            "art": {
                "thumb": self.thumbnail,
                "landscape": self.landscape
            },
            "params": {
                "series_id": self.id
            }

        }
        return res


class Category:
    def __init__(self, item, parent_id=None):
        self.item = item
        self.id = item["id"]
        self.title = item["localization"]["title"]
        self.description = item["localization"]["description"]
        if "image" in item:
            self.fanart = item["images"]["background"][0]
        else:
            self.fanart = codequick.listing.Art().global_thumb("videos.png")
        self.parent_id = parent_id

    def to_dict(self):
        res = {
            "label": self.title,
            "art": {
                "thumbnail": self.fanart
            },
        }
        if self.parent_id:
            res["params"] = {
                "categories": [self.parent_id, self.id]
            }
        else:
            res["params"] = {
                "category_id": self.id
            }
        return res
