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


class Meta(type, metaclass=type("", (type,), {"__str__": lambda _: "~hi"})):
    def __str__(self):
        return "<class 'crunchyroll_beta.types.{self.__name__}'>"


class Object(metaclass=Meta):
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
