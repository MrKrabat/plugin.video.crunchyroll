# -*- coding: utf-8 -*-
# ${LICENSE_HEADER}

# pylint: disable=E0401
import codequick
from . import utils


class Episode:

    def __init__(self, item, playhead):
        self.item = item
        self.playhead = playhead
        self.id = item["id"]
        self.season_number_str = item["episode_metadata"].get("season_number", "1")
        self.number_str = utils.lookup_episode_number(item)
        self.number = utils.number_to_int(self.number_str)
        self.series_title = item["episode_metadata"]["series_title"]
        self.title = item["title"]
        self.label = f"{self.series_title} | {self.season_number_str}#{self.number_str} | {self.title}"
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
