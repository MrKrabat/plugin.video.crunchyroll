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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys

import xbmcgui
import xbmcplugin
import xbmcvfs

try:
    from urllib import unquote_plus
except ImportError:
    from urllib.parse import unquote_plus

from json import dumps

import xbmcaddon


class Args(object):
    """Arguments class
    Hold all arguments passed to the script and also persistent user data and
    reference to the addon. It is intended to hold all data necessary for the
    script.
    """

    def __init__(self, argv, kwargs):
        """Initialize arguments object
        Hold also references to the addon which can't be kept at module level.
        """
        self.mode = None
        self.PY2 = sys.version_info[0] == 2  #: True for Python 2
        self._argv = argv
        self._addonid = self._argv[0][9:-1]
        self._addon = xbmcaddon.Addon(id=self._addonid)
        self._addonname = self._addon.getAddonInfo("name")
        self._cj = None
        self._device_id = None
        self._subtitle = None
        self._subtitle_fallback = None
        # needed to pass some data around
        self._playhead = None
        self.stream_id = None

        for key, value in kwargs.items():
            if value:
                setattr(self, key, unquote_plus(value[0]))

    @property
    def addon(self):
        return self._addon

    @property
    def addonname(self):
        return self._addonname

    @property
    def addonid(self):
        return self._addonid

    @property
    def argv(self):
        return self._argv

    @property
    def device_id(self):
        return self._device_id

    @property
    def subtitle(self):
        return self._subtitle

    @property
    def subtitle_fallback(self):
        return self._subtitle_fallback


class Meta(type):
    def __str__(self):
        return "<class 'crunchyroll_beta.types.{}'>".format(self.__name__)


class Object:
    __metaclass__ = Meta

    def __init__(self):
        pass

    @staticmethod
    def default(obj):
        return dict(
            (("_", obj.__class__.__name__),) +
            tuple(
                (attr, getattr(obj, attr))
                for attr in filter(lambda x: not x.startswith("_"), obj.__dict__)
                if getattr(obj, attr) is not None
            )
        )

    def __str__(self):
        return dumps(self, indent=4, default=Object.default, ensure_ascii=False)


class CMS(Object):
    def __init__(self, data):
        Object.__init__(self)
        self.bucket = data.get("bucket")
        self.policy = data.get("policy")
        self.signature = data.get("signature")
        self.key_pair_id = data.get("key_pair_id")


class AccountData(Object):
    def __init__(self, data):
        Object.__init__(self)
        self.cms = None
        self.expires = None
        self.refresh_token = None
        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token")
        self.expires = data.get("expires")
        self.token_type = data.get("token_type")
        self.scope = data.get("scope")
        self.country = data.get("country")
        self.account_id = data.get("account_id")
        self.cms = CMS(data.get("cms", {}))
        self.service_available = data.get("service_available")
        self.avatar = data.get("avatar")
        self.has_beta = data.get("cr_beta_opt_in")
        self.email_verified = data.get("crleg_email_verified")
        self.email = data.get("email")
        self.maturity_rating = data.get("maturity_rating")
        self.account_language = data.get("preferred_communication_language")
        self.default_subtitles_language = data.get("preferred_content_subtitle_language")
        self.default_audio_language = data.get("preferred_content_audio_language")
        self.username = data.get("username")

    # def to_json(self):
    #   return dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class MovieData(Object):
    def __init__(self, data):
        Object.__init__(self)
        from . import utils

        meta = data.get("panel").get("movie_metadata")

        self.title = meta.get("movie_listing_title", "")
        self.tvshowtitle = meta.get("movie_listing_title", "")
        self.duration = int(meta.get("duration_ms", 0) / 1000)
        self.playhead = data.get("playhead", 0)
        self.episode = "1"
        self.episode_id = data.get("panel", {}).get("id")
        self.collection_id = None
        self.series_id = None
        self.plot = data.get("panel", {}).get("description", "")
        self.plotoutline = data.get("panel", {}).get("description", "")
        self.year = meta.get("premium_available_date")[:10] if meta.get("premium_available_date") is not None else ""
        self.aired = meta.get("premium_available_date")[:10] if meta.get("premium_available_date") is not None else ""
        self.premiered = meta.get("premium_available_date")[:10] if meta.get(
            "premium_available_date") is not None else ""
        self.thumb = utils.get_image_from_struct(data.get("panel"), "thumbnail", 2)
        self.fanart = utils.get_image_from_struct(data.get("panel"), "thumbnail", 2)
        self.playcount = 0
        self.stream_id = None

        try:
            # note that for fetching streams we need a special guid, not the episode_id
            self.stream_id = utils.get_stream_id_from_url(
                data.get("panel", {}).get("__links__", {}).get("streams", {}).get("href", "")
            )

            # history data has the stream_id at a different location
            if self.stream_id is None:
                self.stream_id = utils.get_stream_id_from_url(
                    data.get("panel", {}).get("streams_link")
                )

            if self.stream_id is None:
                raise Exception("")

        except Exception:
            raise CrunchyrollError("Failed to get stream id for %s" % self.title)

        if self.playhead is not None and self.duration is not None:
            self.playcount = 1 if (int(self.playhead / self.duration * 100)) > 90 else 0


# dto
class EpisodeData(Object):
    def __init__(self, data):
        Object.__init__(self)
        from . import utils

        meta = data.get("panel").get("episode_metadata")

        self.title = meta.get("season_title") + " #" + meta.get("episode") + " - " + data.get("panel").get("title")
        self.tvshowtitle = meta.get("series_title", "")
        self.duration = int(meta.get("duration_ms", 0) / 1000)
        self.playhead = data.get("playhead", 0)
        self.episode = meta.get("episode", "")
        self.episode_id = data.get("panel", {}).get("id")
        self.collection_id = meta.get("season_id")
        self.series_id = meta.get("series_id")
        self.plot = data.get("panel", {}).get("description", "")
        self.plotoutline = data.get("panel", {}).get("description", "")
        self.year = meta.get("episode_air_date")[:10] if meta.get("episode_air_date") is not None else ""
        self.aired = meta.get("episode_air_date")[:10] if meta.get("episode_air_date") is not None else ""
        self.premiered = meta.get("episode_air_date")[:10] if meta.get("episode_air_date") is not None else ""
        self.thumb = utils.get_image_from_struct(data.get("panel"), "thumbnail", 2)
        self.fanart = utils.get_image_from_struct(data.get("panel"), "thumbnail", 2)
        self.playcount = 0
        self.stream_id = None

        try:
            # note that for fetching streams we need a special guid, not the episode_id
            self.stream_id = utils.get_stream_id_from_url(
                data.get("panel", {}).get("__links__", {}).get("streams", {}).get("href", "")
            )

            # history data has the stream_id at a different location
            if self.stream_id is None:
                self.stream_id = utils.get_stream_id_from_url(
                    data.get("panel", {}).get("streams_link")
                )

            if self.stream_id is None:
                raise Exception("")

        except Exception:
            raise CrunchyrollError("Failed to get stream id for %s" % self.title)

        if self.playhead is not None and self.duration is not None:
            self.playcount = 1 if (int(self.playhead / self.duration * 100)) > 90 else 0


class CrunchyrollError(Exception):
    pass


class LoginError(Exception):
    pass


class VideoPlayerStreamData(Object):
    def __init__(self):
        self.stream_url = None
        self.subtitle_urls = None


"""
Build a VideoPlayerStream DTO using args.steam_id

Will download stream details from cr api and store the appropriate stream url

It will then check if soft subs are enabled in settings and if so, manage downloading the required subtitles, which
are then renamed to make kodi label them in a readable way - this is because kodi uses the filename of the subtitles
to identify the language and the cr files have cryptic filenames, which will render gibberish to the user on kodi 
instead of a proper label 
"""


class VideoStream(Object):
    def __init__(self, args, api):
        self.api = api
        self.args = args

    def get_player_stream_data(self, stream_id) :
        if not hasattr(self.args, 'stream_id') or not self.args.stream_id:
            return None

        video_player_stream_data = VideoPlayerStreamData

        api_stream_data = self._get_stream_data_from_api()
        if api_stream_data is False:
            raise CrunchyrollError("Failed to fetch stream data from api")

        video_player_stream_data.stream_url = self._get_stream_url_from_api_data(api_stream_data)
        video_player_stream_data.subtitle_urls = self._get_subtitles_from_api_data(api_stream_data)

        return video_player_stream_data

    """ get json stream data from cr api for given args.stream_id """
    def _get_stream_data_from_api(self):
        # api request streams
        req = self.api.make_request(
            method="GET",
            url=self.api.STREAMS_ENDPOINT.format(self.api.account_data.cms.bucket, self.args.stream_id),
            params={
                "locale": self.args.subtitle
            }
        )

        # check for error
        if "error" in req or req is None:
            item = xbmcgui.ListItem(getattr(self.args, "title", "Title not provided"))
            xbmcplugin.setResolvedUrl(int(self.args.argv[1]), False, item)
            xbmcgui.Dialog().ok(self.args.addonname, self.args.addon.getLocalizedString(30064))
            return False

        return req

    """ retrieve appropriate stream url from api data """
    def _get_stream_url_from_api_data(self, api_data):
        try:
            if self.args.addon.getSetting("soft_subtitles") == "false":
                url = api_data["streams"]["adaptive_hls"]
                if self.args.subtitle in url:
                    url = url[self.args.subtitle]["url"]
                elif self.args.subtitle_fallback in url:
                    url = url[self.args.subtitle_fallback]["url"]
                else:
                    url = url[""]["url"]
            else:
                # multitrack_adaptive_hls_v2 includes soft subtitles in the stream
                url = api_data["streams"]["multitrack_adaptive_hls_v2"][""]["url"]

        except IndexError:
            item = xbmcgui.ListItem(getattr(self.args, "title", "Title not provided"))
            xbmcplugin.setResolvedUrl(int(self.args.argv[1]), False, item)
            xbmcgui.Dialog().ok(self.args.addonname, self.args.addon.getLocalizedString(30064))
            return None

        return url

    """ retrieve appropriate subtitle urls from api data, using local caching and renaming """
    def _get_subtitles_from_api_data(self, api_stream_data):
        # we only need those urls if softsubs are enabled in addon settings
        if self.args.addon.getSetting("soft_subtitles") == "false":
            return None

        subtitles_data_raw = []
        subtitles_url_cached = []

        if self.args.subtitle in api_stream_data["subtitles"]:
            subtitles_data_raw.append(api_stream_data.get("subtitles").get(self.args.subtitle))
        elif self.args.subtitle_fallback and self.args.subtitle_fallback in api_stream_data["subtitles"]:
            subtitles_data_raw.append(api_stream_data.get("subtitles").get(self.args.subtitle_fallback))
        else:
            return None

        # we need to download the subtitles, cache and rename them to show proper labels in the kodi video player
        for subtitle_data in subtitles_data_raw:
            cache_result = self._get_subtitle_from_cache(
                subtitle_data.get('url', ""),
                subtitle_data.get('locale', ""),
                subtitle_data.get('format', "")
            )

            if cache_result is not None:
                subtitles_url_cached.append(cache_result)

        return subtitles_url_cached if subtitles_url_cached is not None else None

    """ cache a subtitle from the given url and rename it for kodi to label it correctly """
    def _cache_subtitle(self, subtitle_url, subtitle_language: str, subtitle_format: str) -> bool:
        try:
            # api request streams
            subtitles_string = self.api.make_request(
                method="GET",
                url=subtitle_url
            )
        except Exception:
            raise CrunchyrollError(
                "Failed to download subtitle for language %s from url %s" % (subtitle_language, subtitle_url)
            )

        if subtitles_string is not str or not subtitles_string:
            # error
            raise CrunchyrollError("Returned data is not text")

        cache_target = xbmcvfs.translatePath(self.get_cache_path() + self.args.stream_id)
        xbmcvfs.mkdirs(cache_target)

        cache_file = 'test' + '.' + subtitle_language + '.' + subtitle_format
        with open(cache_target + cache_file, 'w') as file:
            result = file.write(subtitles_string)

        return True if result > 0 else False

    """ try to get a subtitle using it's url, language info and format. may call _cache_subtitle if it doesn't exist """
    def _get_subtitle_from_cache(self, subtitle_url, subtitle_language, subtitle_format):
        if not subtitle_url or not subtitle_language or not subtitle_format:
            # todo: log error
            return None

        # prepare the filename for the subtitles
        cache_file = 'test' + '.' + subtitle_language + '.' + subtitle_format
        # build full path to cached file
        cache_target = xbmcvfs.translatePath(self.get_cache_path() + self.args.stream_id) + cache_file

        # check if cached file exists
        if not xbmcvfs.exists(cache_target):
            # download and cache file
            if not self._cache_subtitle(subtitle_url, subtitle_language, subtitle_format):
                # log error
                return None

        cache_file_url = 'special://userdata/addon_data/plugin.video.crunchyroll/cache_subtitles/' + cache_file

        return cache_file_url

    """ clean up all cached subtitles """
    def _clean_cache_subtitles(self):
        # todo
        return True

    """ return base path for subtitles caching """
    def get_cache_path(self):
        return xbmcvfs.translatePath(self.args.addon.getAddonInfo("profile") + '/cache_subtitles/')
