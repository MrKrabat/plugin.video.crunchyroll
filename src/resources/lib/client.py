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
from . import auth, utils
from .model import Series, Season, Episode, Category
import xbmc

class CrunchyrollClient:


    def _log(self, msg):
        xbmc.log(f"[Crunchyroll-Client] {msg}")

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
            response = requests.post(url, params=params, headers=headers, auth=self.auth, json=data)
        else:
            response = requests.post(url, params=params, headers=headers, auth=self.auth, data=data)
        response.raise_for_status()
        return response


    def _get(self, url, params={}, headers={}):
        headers['User-Agent'] = "Crunchyroll/3.10.0 Android/6.0 okhttp/4.9.1"
        response = requests.get(url, params=params, headers=headers, auth=self.auth)
        response.raise_for_status()
        return response

    def _get_cms(self, url, params={}, headers={}):
        params["Policy"] = self.cms['policy']
        params["Signature"] = self.cms['signature']
        params["Key-Pair-Id"] = self.cms['key_pair_id']
        response = self._get(url, params=params, headers=headers)
        response.raise_for_status()
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
        response.raise_for_status()
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
        playheads = self.get_playhead(map(lambda item: item['panel']['id'], data['items']))
        result = []
        for item in data['items']:
            item = item['panel']
            playhead = utils.lookup_playhead(playheads['data'], item['id'])
            result.append(Episode(item, playhead))

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
        response.raise_for_status()
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
        response.raise_for_status()
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
        response.raise_for_status()
        raw_data = response.json()
        list_ids = list(map(lambda item: item['id'], raw_data['items']))
        playheads = self.get_playhead(list_ids)
        episodes = self.get_episodes(list_ids)
        res = []
        for item in raw_data['items']:
            episode = utils.lookup_episode(episodes['items'], item['id'])
            playhead = utils.lookup_playhead(playheads['data'], item['id'])
            res.append(Episode(episode, playhead))
        return res

    def get_episodes(self, id_list):
        episodes = ",".join(id_list)
        self._log(f"Get episodes {episodes}")
        url = f"https://beta-api.crunchyroll.com/cms/v2{self.cms['bucket']}/objects/{episodes}"
        params = {
            "locale": self.locale
        }
        response = self._get_cms(url, params=params)
        return response.json()


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
        if self.locale in data['streams']['adaptive_hls']:
            url = data['streams']['adaptive_hls'][self.locale]["url"]
        elif 'en-US' in data['streams']['adaptive_hls']:
            url = data['streams']['adaptive_hls']["en-US"]["url"]
        else:
            url = data['streams']['adaptive_hls'][""]["url"]
        return url

    def get_playhead(self, id_list):
        episodes = ','.join(id_list)
        self._log(f"Getting playhead of episodes {episodes}")
        params = {
            "content_ids": episodes
        }
        url = f"https://beta-api.crunchyroll.com/content/v2/{self.auth.data['account_id']}/playheads"
        data = self._get(url, params=params).json()
        return data
        

    def update_playhead(self, episode_id, time):
        self._log(f"Update playhead of episode {episode_id} with time {time}")
        url = f"https://beta-api.crunchyroll.com/content/v2/{self.auth.data['account_id']}/playheads"
        data = {
            "content_id": episode_id,
            "playhead": time
        }
        self._post(url, data=data, json=True)


    def browse(self, sort_by=None, start=0, number=10, categories=[], seasonal_tag=None):
        url = "https://beta-api.crunchyroll.com/content/v2/discover/browse"
        params = {
            "n": number,
            "locale": self.locale,
            "start": start
        }
        if sort_by:
            params['sort_by'] = sort_by
        if len(categories) > 0:
            params['categories'] = ",".join(categories)
        if seasonal_tag:
            params['seasonal_tag'] = seasonal_tag

        response = self._get(url, params=params)
        response.raise_for_status()
        data = response.json()
        result = []
        for item in data['data']:
            result.append(Series(item))
        nextLink=None
        if "__links__" in data and "continuation" in data['__links__']:
            nextLink = {"start":start+number}
        return result, nextLink

    def browse_index(self, sort_by):
        url = "https://beta-api.crunchyroll.com/content/v2/discover/browse/index"
        params = {
            "locale": self.locale,
            "sort_by": sort_by,
        }
        response = self._get(url, params=params)
        response.raise_for_status()
        return response.json()

    def alpha(self):
        data = self.browse_index('alphabetical')
        result=[]
        for item in data['data']:
            result.append({
                'prefix': item['prefix'],
                'start': item['offset'],
                'number': item['total']
            })
        return result

    def popular(self, start=0, number=10, categories=[]):
        self._log(f"Looking up for popular animes from {start}")
        return self.browse(sort_by="popularity", start=start, number=number, categories=categories)

    def newly_added(self, start=0, number=10, categories=[]):
        self._log(f"Looking up for animes to discover from {start}")
        return self.browse(sort_by="newly_added", start=start, number=number, categories=categories)

    def get_categories(self):
        url = "https://beta-api.crunchyroll.com/content/v2/discover/categories"
        params = {
            "locale": self.locale
        }
        response = self._get(url, params=params)
        response.raise_for_status()
        data = response.json()
        res = []
        for category in data['data']:
            res.append(Category(category))
        return res

    def get_sub_categories(self, parent_id):
        url = f"https://beta-api.crunchyroll.com/content/v2/discover/categories/{parent_id}/sub_categories"
        params = {
            "locale": self.locale
        }
        response = self._get(url, params=params)
        response.raise_for_status()
        data = response.json()
        res = []
        for category in data['data']:
            res.append(Category(category, parent_id))
        return res

    def get_seasonal_tags(self):
        url="https://beta-api.crunchyroll.com/content/v2/discover/seasonal_tags"
        params = {
            "locale": self.locale
        }
        response = self._get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data['data']
