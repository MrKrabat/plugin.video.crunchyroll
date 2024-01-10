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

import requests
import xbmc
import m3u8
from . import auth, utils
from .model import Series, Season, Episode, Category


class CrunchyrollClient:

    def _log(self, msg):
        xbmc.log(f"[Crunchyroll-Client] {msg}")

    # pylint: disable=R0913
    def __init__(self, email, password, locale, page_size, resolution):
        self.auth = auth.CrunchyrollAuth(email, password)
        self.locale = locale
        self.page_size = page_size
        self.cms = self._get_cms_info()
        self.resolution = resolution

    def _get_cms_info(self):
        url = f"{utils.CRUNCHYROLL_BASE_URL}/index/v2"
        response = self._get(url)
        return response.json()['cms']

    # pylint: disable=W0102
    def _post(self, url, params={}, headers={}, data={}, json=False):
        headers['User-Agent'] = utils.CRUNCHYROLL_UA
        if json:
            response = requests.post(url, params=params, headers=headers, auth=self.auth, json=data, timeout=30)
        else:
            response = requests.post(url, params=params, headers=headers, auth=self.auth, data=data, timeout=30)
        response.raise_for_status()
        return response

    # pylint: disable=W0102
    def _get(self, url, params={}, headers={}):
        headers['User-Agent'] = utils.CRUNCHYROLL_UA
        params['locale'] = self.locale
        response = requests.get(url, params=params, headers=headers, auth=self.auth, timeout=30)
        response.raise_for_status()
        return response

    # pylint: disable=W0102
    def _get_cms(self, url, params={}, headers={}):
        params["Policy"] = self.cms['policy']
        params["Signature"] = self.cms['signature']
        params["Key-Pair-Id"] = self.cms['key_pair_id']
        response = self._get(url, params=params, headers=headers)
        return response

    def get_watchlist(self, start=0):
        self._log("Showing watchlist")
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v1/{self.auth.data['account_id']}/watchlist"
        params = {
            "n": self.page_size,
            "start": start
        }
        data = self._get(url, params=params).json()
        playheads = self.get_playhead(map(lambda item: item['panel']['id'], data['items']))
        res = []
        for item in data['items']:
            item = item['panel']
            playhead = utils.lookup_playhead(playheads['data'], item['id'])
            res.append(Episode(item, playhead))

        next_link = None
        if start + self.page_size < data['total']:
            next_link = {"start": start + self.page_size}
        return res, next_link

    def search_anime(self, query, start=0):
        self._log(f"Looking up for animes with query {query}, from {start}")
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v2/discover/search"
        params = {
            "q": query,
            "n": self.page_size,
            "type": "series",
            "start": start
        }
        data = self._get(url, params=params).json()
        res = []
        for item in data['data'][0]['items']:
            res.append(Series(item))
        next_link = None
        if start + self.page_size < data['data'][0]['count']:
            next_link = {"start": start + self.page_size}
        return res, next_link

    def get_history(self, page=1):
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v2/{self.auth.data['account_id']}/watch-history"
        params = {
            "page_size": self.page_size,
            "page": page
        }
        data = self._get(url, params=params).json()
        playheads = self.get_playhead(map(lambda item: item['panel']['id'], data['data']))
        res = []
        for item in data['data']:
            playhead = utils.lookup_playhead(playheads['data'], item['id'])
            res.append(Episode(item['panel'], playhead))
        next_link = None
        if page * self.page_size < data['total']:
            next_link = {"page": page + 1}
        return res, next_link

    def get_crunchylists(self):
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v2/{self.auth.data['account_id']}/custom-lists"
        data = self._get(url).json()
        return data['data']

    def get_crunchylist(self, list_id):
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v2/{self.auth.data['account_id']}/custom-lists/{list_id}"
        data = self._get(url).json()
        res = []
        for item in data['data']:
            res.append(Series(item['panel']))
        return res

    def get_series_seasons(self, series_id):
        self._log(f"Get seasons of series {series_id}")
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v2/cms/series/{series_id}/seasons"
        data = self._get(url).json()
        res = []
        for item in data['data']:
            res.append(Season(item))
        return res

    def get_season_episodes(self, season_id):
        self._log(f"Get episodes of seasons {season_id}")
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v2/cms/seasons/{season_id}/episodes"
        data = self._get(url).json()
        list_ids = list(map(lambda item: item['id'], data['data']))
        playheads = self.get_playhead(list_ids)
        episodes = self.get_objects(list_ids)
        res = []
        for item in data['data']:
            episode = utils.lookup_episode(episodes['data'], item['id'])
            playhead = utils.lookup_playhead(playheads['data'], item['id'])
            res.append(Episode(episode, playhead))
        return res

    def get_objects(self, id_list):
        objects = ",".join(id_list)
        self._log(f"Get objects {objects}")
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v2/cms/objects/{objects}"
        response = self._get(url)
        return response.json()

    def get_stream_url(self, episode_id):
        self._log(f"Get streams for episode id {episode_id}")
        episode = self.get_objects([episode_id])["data"][0]
        audio_local = episode['episode_metadata']['audio_locale']
        for version in episode['episode_metadata']['versions']:
            if version['audio_locale'] == audio_local:
                stream_id = version['media_guid']
        self._log(f"Resolved stream id {stream_id}")
        url = f"{utils.CRUNCHYROLL_BASE_URL}/cms/v2{self.cms['bucket']}/videos/{stream_id}/streams"
        data = self._get_cms(url).json()
        playlist = m3u8.load(utils.lookup_playlist_url(data['streams']['adaptive_hls'], self.locale))
        return utils.lookup_stream_url(playlist.playlists, self.resolution)

    def get_playhead(self, id_list):
        episodes = ','.join(id_list)
        self._log(f"Getting playhead of episodes {episodes}")
        params = {
            "content_ids": episodes
        }
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v2/{self.auth.data['account_id']}/playheads"
        data = self._get(url, params=params).json()
        return data

    def update_playhead(self, episode_id, time):
        self._log(f"Update playhead of episode {episode_id} with time {time}")
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v2/{self.auth.data['account_id']}/playheads"
        data = {
            "content_id": episode_id,
            "playhead": time
        }
        self._post(url, data=data, json=True)

    def browse(self, sort_by=None, start=0, number=10, categories=[], seasonal_tag=None):
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v2/discover/browse"
        params = {
            "n": number,
            "start": start
        }
        if sort_by:
            params['sort_by'] = sort_by
        if len(categories) > 0:
            params['categories'] = ",".join(categories)
        if seasonal_tag:
            params['seasonal_tag'] = seasonal_tag

        data = self._get(url, params=params).json()
        res = []
        for item in data['data']:
            res.append(Series(item))
        next_link = None
        if start + number < data['total']:
            next_link = {"start": start + number}
        return res, next_link

    def browse_index(self, sort_by):
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v2/discover/browse/index"
        params = {
            "sort_by": sort_by
        }
        response = self._get(url, params=params)
        return response.json()

    def get_alpha(self):
        data = self.browse_index('alphabetical')
        res = []
        for item in data['data']:
            res.append({
                'prefix': item['prefix'],
                'start': item['offset'],
                'number': item['total']
            })
        return res

    def get_popular(self, start=0, categories=[]):
        self._log(f"Looking up for popular animes from {start}")
        return self.browse(sort_by="popularity", start=start, number=self.page_size, categories=categories)

    def get_newly_added(self, start=0, categories=[]):
        self._log(f"Looking up for animes to discover from {start}")
        return self.browse(sort_by="newly_added", start=start, number=self.page_size, categories=categories)

    def get_categories(self):
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v2/discover/categories"
        data = self._get(url).json()
        res = []
        for category in data['data']:
            res.append(Category(category))
        return res

    def get_sub_categories(self, parent_id):
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v2/discover/categories/{parent_id}/sub_categories"
        data = self._get(url).json()
        res = []
        for category in data['data']:
            res.append(Category(category, parent_id))
        return res

    def get_seasonal_tags(self):
        url = f"{utils.CRUNCHYROLL_BASE_URL}/content/v2/discover/seasonal_tags"
        data = self._get(url).json()
        return data['data']
