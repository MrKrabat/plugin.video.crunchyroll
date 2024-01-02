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

class Episode:

    def __init__(self,item, playhead):
        self.item = item
        self.playhead = playhead
        self.id = item["id"]
        self.label = item['episode_metadata']["series_title"] + " #" + str(item["episode_metadata"]["episode_number"]) + " - " + item["title"]
        self.thumbnail = item['images']['thumbnail'][0][0]['source']
        self.landscape =  item['images']['thumbnail'][0][-1]['source']
        self.duration = item['episode_metadata']["duration_ms"]/1000
        self.description = item["description"]
        self.percentplayed = int((playhead['playhead']/self.duration)*100)
        self.playcount = 1 if self.percentplayed > 90 else 0

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
            "info":{
                "duration": self.duration,
                "plot": self.description,
                "episode": self.item["episode_metadata"]["episode_number"],
                "tvshowtitle": self.item['episode_metadata']["series_title"],
                "season": self.item['episode_metadata']['season_number'],
                "percentplayed": self.percentplayed,
                "playcount": self.playcount
            },
            "params": {
                "id": self.id
            }
            
        }
        return res
        

class Season:

    def __init__(self,item):
        self.item = item
        self.id = item['id']
        self.label = item["title"]

    # Format info for codequick
    def to_dict(self):
        res = {
            "label": self.label,
            "params": {
                "id": self.id
            }

        }
        return res


class Series:

    def __init__(self, item):
        self.item = item
        self.id = item['id']
        self.label = item["title"]
        self.thumbnail = item["images"]["poster_tall"][0][3]['source']
        self.landscape = item["images"]["poster_wide"][0][-1]['source']


    # Format info for codequick
    def to_dict(self):
        res = {
            "label": self.label,
            "art": {
                "thumb": self.thumbnail,
                "landscape": self.landscape
            },
            "params": {
                "id": self.id
            }

        }
        return res

class Gender:
    def __init__(self, item):
        self.item = item
        self.id = item['id']
        self.title = item['localization']['title']
        self.description = item['localization']['description']
        self.fanart = item['image']['background'][-1]

    def to_dict(self):
        res = {
            'label': self.title,
            'art': {
                'landscape': self.fanart
            },
            "params": {
                "id": self.id
            }
            
        }
        return res
    
