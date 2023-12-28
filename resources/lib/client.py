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
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import json
import requests
from . import auth
from .model import Series, Season, Episode

class CrunchyrollClient:


    def _log(self, msg):
        print(f"[Crunchyroll-Client] {msg}")

    def __init__(self, email, password, locale):
        self.auth = auth.CrunchyrollAuth(email, password)
        self.cms = self._get_cms_info()
        self.locale = locale


    def _get_cms_info(self):
        url="https://beta-api.crunchyroll.com/index/v2"
        response = self._get(url)
        return response.json()['cms']


    def _post(self, url, params={}, headers={}, data={}, json=False):
        headers['User-Agent'] = "Crunchyroll/3.10.0 Android/6.0 okhttp/4.9.1"
        if json:
            response = requests._get(url, params=params, headers=headers, auth=self.auth, json=data)
        else:
            response = requests._get(url, params=params, headers=headers, auth=self.auth, data=data)
        return response


    def _get(self, url, params={}, headers={}):
        headers['User-Agent'] = "Crunchyroll/3.10.0 Android/6.0 okhttp/4.9.1"
        response = requests.get(url, params=params, headers=headers, auth=self.auth)
        return response

    def _get_cms(self, url, params={}, headers={}):
        params["Policy"] = self.cms['policy']
        params["Signature"] = self.cms['signature']
        params["Key-Pair-Id"] = self.cms['key_pair_id']
        response = self._get(url, params=params, headers=headers)
        # TODO handle errors
        return response

    # Continue watching
    def get_queue(self,start=0):
        self._log(f"List queued episode from {start}")
        url = f"https://beta-api.crunchyroll.com/content/v1/{self.auth.data['account_id']}/continue_watching"
        params = {
            "n": 10,
            "start": start,
            "locale": self.locale
        }

        response = self._get(url,params=params)
        # TODO handle errors
        return response.json()


    def watchlist(self, start=0, number=10):
        self._log(f"Showing watchlist")
        url = f"https://beta-api.crunchyroll.com/content/v1/{self.auth.data['account_id']}/watchlist"
        params = {
            "n": number,
            "locale": self.locale,
            "start": start
        }
        response = self._get(url, params=params)
        data = response.json()
        result = []
        for item in data['items']:
            item = item['panel']
            result.append(Episode(item))

        nextLink=None
        if "__links__" in data and "continuation" in data['__links__']:
            nextLink = {"start":start+number}
        return result, nextLink


    def search_anime(self, query, start=0, number=10):
        # TODO add a preference for pagination length
        self._log(f"Looking up for animes with query {query}, from {start}")
        url = "https://beta-api.crunchyroll.com/content/v1/search"
        params = {
            "q": query,
            "n": number,
            "locale": self.locale,
            "type": "series",
            "start": start
        }
        response = self._get(url, params=params)
        # TODO handle errors
        data = response.json()
        result = []
        for item in data['items'][0]['items']:
            result.append(Series(item))
        nextLink=None
        if "__links__" in data and "continuation" in data['__links__']:
            nextLink = {"start":start+number}
        return result, nextLink


    def get_history(self):
        print("Not Yet Implemented")


    def get_series_seasons(self, series_id):
        self._log(f"Get seasons of series {series_id}")
        url = f"https://beta-api.crunchyroll.com/cms/v2{self.cms['bucket']}/seasons"
        params = {
            "series_id": series_id,
            "locale": self.locale
        }
        response = self._get_cms(url, params=params)
        # TODO handle errors
        data = response.json()
        result = []
        for item in data['items']:
            result.append(Season(item))
        return result



    def get_season_episodes(self, season_id):
        self._log(f"Get episodes of seasons {season_id}")
        url = f"https://beta-api.crunchyroll.com/cms/v2{self.cms['bucket']}/episodes"
        params = {
            "season_id": season_id
        }
        response = self._get_cms(url, params=params)
        # TODO handle errors
        data = response.json()
        res = []
        for item in data['items']:
            episode = self.get_episode(item['id'])['items'][0]
            res.append(Episode(episode))
        return res

    def get_episode(self, episode_id):
        self._log(f"Get episode {episode_id}")
        url = f"https://beta-api.crunchyroll.com/cms/v2{self.cms['bucket']}/objects/{episode_id}"
        params = {
            "locale": self.locale
        }
        response = self._get_cms(url, params=params)
        return response.json()

    def get_stream_url(self, id):
        self._log(f"Get streams for episode id {id}")
        episode = self.get_episode(id)["items"][0]
        audio_local = episode['episode_metadata']['audio_locale']
        for version in episode['episode_metadata']['versions']: 
            if version['audio_locale'] == audio_local:
                stream_id = version['media_guid']
        self._log(f"Resolved stream id {stream_id}")
        url = f"https://beta-api.crunchyroll.com/cms/v2{self.cms['bucket']}/videos/{stream_id}/streams"
        data = self._get_cms(url).json()
        return data['streams']['adaptive_hls'][audio_local]["url"]


    def update_playhead(self, episode_id, time):
        self._log(f"Update playhead of episode {episode_id} with time {time}")
        url = f"https://beta-api.crunchyroll.com/content/v1/playheads/{self.auth.data['account_id']}"
        data = {
            "content_id": episode_id,
            "playhead": time
        }
        self._post(url, data=data, json=True)


    def browse(self, sort_by, start=0, number=10):
        url = "https://beta-api.crunchyroll.com/content/v1/browse"
        params = {
            "n": number,
            "locale": self.locale,
            "sort_by": sort_by,
            "start": start
        }
        response = self._get(url, params=params)
        # TODO handle errors
        data = response.json()
        result = []
        import json
        print(json.dumps(data,indent=4))
        for item in data['items']:
            result.append(Series(item))
        nextLink=None
        if "__links__" in data and "continuation" in data['__links__']:
            nextLink = {"start":start+number}
        return result, nextLink

    def popular(self, start=0, number=10):
        self._log(f"Looking up for popular animes from {start}")
        return self.browse("popularity", start, number)

    def newly_added(self, start=0, number=10):
        self._log(f"Looking up for animes to discover from {start}")
        return self.browse("newly_added", start, number)
