# -*- coding: utf-8 -*-
# ${LICENSE_HEADER}

# pylint: disable=E0401
import json
from . import utils


class CrunchryrollModelBase:

    def to_dict(self):
        return {}

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)


class Episode(CrunchryrollModelBase):

    def __init__(self, item, playhead):
        self.item = item
        self.playhead = playhead
        self.id = item["id"]
        self.season_number = item["episode_metadata"].get("season_number", 1)
        self.number_str = utils.lookup_episode_number(item)
        self.number = utils.number_to_int(self.number_str)
        self.series_title = item["episode_metadata"]["series_title"]
        self.title = item["title"]
        self.label = f"{self.series_title} | {self.season_number}#{self.number_str} | {self.title}"
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
                "season": self.season_number,
                "tvshowtitle": self.item["episode_metadata"]["series_title"],
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
            if int((self.playhead["playhead"] / self.duration) * 100) < 1:
                res["info"]["playcount"] = 0
            else:
                res["properties"]["resumetime"] = self.playhead["playhead"]

        return res


class Season(CrunchryrollModelBase):

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


class Series(CrunchryrollModelBase):

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


class Category(CrunchryrollModelBase):
    def __init__(self, item, parent_id=None):
        self.item = item
        self.id = item["id"]
        self.title = item["localization"]["title"]
        self.description = item["localization"]["description"]
        self.fanart = None
        self.background = None
        if item.get('images', None):
            if item['images'].get('low', None):
                self.fanart = item["images"]["low"][-1]['source']
            if item['images'].get('background', None):
                self.background = item['images']['background'][-1]['source']
        self.parent_id = parent_id

    def to_dict(self):
        res = {
            "label": self.title,
            "art": {}
        }
        if self.fanart:
            res["art"]["thumb"] = self.fanart

        if self.background:
            res["art"]["fanart"] = self.background

        if self.parent_id:
            res["params"] = {
                "categories_list": [self.parent_id, self.id]
            }
        else:
            res["params"] = {
                "category_id": self.id
            }
        return res


class User(CrunchryrollModelBase):
    def __init__(self, user):
        self.id = user['profile_id']
        self.avatar = user.get('avatar', '0006-cr-white-black.png')
        self.wallpaper = user.get('wallpaper', 'crbrand_product_multipleprofilesbackgroundassets_4k-01.png')
        self.name = user['profile_name']

    def to_dict(self):
        res = {
            "label": self.name,
            "art": {
                "thumb": f"https://static.crunchyroll.com/assets/avatar/510x510/{self.avatar}",
                "fanart": f"https://static.crunchyroll.com/assets/wallpaper/1920x1080/{self.wallpaper}"
            }
        }
        return res
