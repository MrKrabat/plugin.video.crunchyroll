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
from abc import abstractmethod
from typing import Any, Dict, Union

import xbmcgui
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
        # addon specific data
        self.PY2 = sys.version_info[0] == 2  #: True for Python 2
        self._argv = argv
        self._addonid = self._argv[0][9:-1]
        self._addon = xbmcaddon.Addon(id=self._addonid)
        self._addonname = self._addon.getAddonInfo("name")
        self._cj = None
        self._device_id = None
        self._args: dict = {}  # holds all parameters provided via URL

        # data from settings
        self._subtitle = None
        self._subtitle_fallback = None

        # copy url args to self._args
        for key, value in kwargs.items():
            if value:
                self._args[key] = unquote_plus(value[0])

    def get_arg(self, arg: str, default: Any = None, cast: type = None):
        """ Get an argument provided via URL"""
        value = self._args.get(arg, default)
        if cast:
            value = cast(value)
        return value

    def set_arg(self, key: str, value=Any):
        self._args[key] = value

    def set_args(self, data: Union[Dict, dict, list]):
        self._args.update(data)

    @property
    def addon(self):
        return self._addon

    @property
    def addon_name(self):
        return self._addonname

    @property
    def addon_id(self):
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

    @property
    def args(self):
        return self._args


class Meta(type, metaclass=type("", (type,), {"__str__": lambda _: "~hi"})):
    def __str__(self):
        return f"<class 'crunchyroll_beta.types.{self.__name__}'>"


class Object(metaclass=Meta):
    @staticmethod
    def default(obj: "Object"):
        return {
            "_": obj.__class__.__name__,
            **{
                attr: (
                    getattr(obj, attr)
                )
                for attr in filter(lambda x: not x.startswith("_"), obj.__dict__)
                if getattr(obj, attr) is not None
            }
        }

    def __str__(self) -> str:
        return dumps(self, indent=4, default=Object.default, ensure_ascii=False)


class CMS(Object):
    def __init__(self, data: dict):
        self.bucket: str = data.get("bucket")
        self.policy: str = data.get("policy")
        self.signature: str = data.get("signature")
        self.key_pair_id: str = data.get("key_pair_id")


class AccountData(Object):
    def __init__(self, data: dict):
        self.access_token: str = data.get("access_token")
        self.refresh_token: str = data.get("refresh_token")
        self.expires: str = data.get("expires")
        self.token_type: str = data.get("token_type")
        self.scope: str = data.get("scope")
        self.country: str = data.get("country")
        self.account_id: str = data.get("account_id")
        self.cms: CMS = CMS(data.get("cms", {}))
        self.service_available: bool = data.get("service_available")
        self.avatar: str = data.get("avatar")
        self.has_beta: bool = data.get("cr_beta_opt_in")
        self.email_verified: bool = data.get("crleg_email_verified")
        self.email: str = data.get("email")
        self.maturity_rating: str = data.get("maturity_rating")
        self.account_language: str = data.get("preferred_communication_language")
        self.default_subtitles_language: str = data.get("preferred_content_subtitle_language")
        self.default_audio_language: str = data.get("preferred_content_audio_language")
        self.username: str = data.get("username")


class ListableItem(Object):
    """ Base object for all DataObjects below that can be displayed in a Kodi List View """

    def __init__(self):
        super().__init__()
        # just a very few that all child classes have in common, so I can spare myself of using hasattr() and getattr()
        self.id: str | None = None
        self.series_id: str | None = None
        self.season_id: str | None = None
        self.title: str | None = None
        self.thumb: str | None = None
        self.fanart: str | None = None
        self.poster: str | None = None
        self.banner: str | None = None

    @abstractmethod
    def get_info(self, args: Args) -> Dict:
        """ return a dict with info to set on the kodi ListItem (filtered) and access some data """

        pass

    def to_item(self, args: Args) -> xbmcgui.ListItem:
        """ Convert ourselves to a Kodi ListItem"""

        from resources.lib.view import types

        info = self.get_info(args)
        # filter out items not known to kodi
        list_info = {key: info[key] for key in types if key in info}

        li = xbmcgui.ListItem()
        li.setLabel(self.title)

        # if is a playable item, set some things
        if hasattr(self, 'duration'):
            li.setProperty("IsPlayable", "true")
            li.setProperty('TotalTime', str(float(getattr(self, 'duration'))))
            # set resume if not fully watched and playhead > x
            if hasattr(self, 'playcount') and getattr(self, 'playcount') == 0:
                if hasattr(self, 'playhead') and getattr(self, 'playhead') > 0:
                    resume = int(getattr(self, 'playhead') / getattr(self, 'duration') * 100)
                    if 5 <= resume <= 90:
                        li.setProperty('ResumeTime', str(float(getattr(self, 'playhead'))))

        li.setInfo('video', list_info)
        li.setArt({
            "thumb": self.thumb or 'DefaultFolder.png',
            'poster': self.poster or self.thumb or 'DefaultFolder.png',
            'banner': self.thumb or 'DefaultFolder.png',
            'fanart': self.fanart or xbmcvfs.translatePath(args.addon.getAddonInfo('fanart')),
            'icon': self.thumb or 'DefaultFolder.png'
        })

        return li

    def update_playcount_from_playhead(self, playhead_data: Dict):
        if not isinstance(self, (EpisodeData, MovieData)):
            return

        setattr(self, 'playhead', playhead_data.get('playhead'))
        if playhead_data.get('fully_watched'):
            setattr(self, 'playcount', 1)
        else:
            self.recalc_playcount()


"""Naming convention for reference:
    Crunchyroll           XBMC
    series                collection
    season                season
    episode               episode   
"""


class SeriesData(ListableItem):
    """ A Series containing Seasons containing Episodes """

    def __init__(self, data: dict):
        super().__init__()
        from . import utils

        panel = data.get('panel') or data
        meta = panel.get("series_metadata") or panel

        self.id = panel.get("id")
        self.title: str = panel.get("title")
        self.tvshowtitle: str = panel.get("title")
        self.series_id: str | None = panel.get("id")
        self.season_id: str | None = None
        self.plot: str = panel.get("description", "")
        self.plotoutline: str = panel.get("description", "")
        self.year: str = str(meta.get("series_launch_year")) + '-01-01'
        self.aired: str = str(meta.get("series_launch_year")) + '-01-01'
        self.premiered: str = str(meta.get("series_launch_year"))
        self.episode: int = meta.get('episode_count')
        self.season: int = meta.get('season_count')

        self.thumb: str | None = utils.get_img_from_struct(panel, "poster_tall", 2)
        self.fanart: str | None = utils.get_img_from_struct(panel, "poster_wide", 2)
        self.poster: str | None = utils.get_img_from_struct(panel, "poster_tall", 2)
        self.banner: str | None = None
        self.rating: int = 0
        self.playcount: int = 0

    def recalc_playcount(self):
        # @todo: not sure how to get that without checking all child seasons and their episodes
        pass

    def get_info(self, args: Args) -> Dict:
        # in theory, we could also omit this method and just iterate over the objects properties and use them
        # to set data on the Kodi ListItem, but this way we are decoupled from their naming convention
        return {
            'title': self.title,
            'tvshowtitle': self.tvshowtitle,
            'season': self.season,
            'episode': self.episode,
            'plot': self.plot,
            'plotoutline': self.plotoutline,

            'playcount': self.playcount,
            'series_id': self.series_id,

            'year': self.year,
            'aired': self.aired,
            'premiered': self.premiered,

            'rating': self.rating,

            'mediatype': 'season',

            # internally used for routing
            "mode": "seasons"
        }


class SeasonData(ListableItem):
    """ A Season/Arc of a Series containing Episodes """

    def __init__(self, data: dict):
        super().__init__()

        self.id = data.get("id")
        self.title: str = data.get("title")
        self.tvshowtitle: str = data.get("title")
        self.series_id: str | None = data.get("series_id")
        self.season_id: str | None = data.get("id")
        self.plot: str = ""  # does not have description. maybe object endpoint?
        self.plotoutline: str = ""
        self.year: str = ""
        self.aired: str = ""
        self.premiered: str = ""
        self.episode: int = 0  # @todo we want to display that, but it's not in the data
        self.season: int = data.get('season_number')
        self.thumb: str | None = None
        self.fanart: str | None = None
        self.poster: str | None = None
        self.banner: str | None = None
        self.rating: int = 0
        self.playcount: int = 1 if data.get('is_complete') == 'true' else 0

        self.recalc_playcount()

    def recalc_playcount(self):
        # @todo: not sure how to get that without checking all child episodes
        pass

    def get_info(self, args: Args) -> Dict:
        return {
            'title': self.title,
            'tvshowtitle': self.tvshowtitle,
            'season': self.season,
            'episode': self.episode,
            # 'plot': self.plot,
            # 'plotoutline': self.plotoutline,

            'playcount': self.playcount,
            'series_id': self.series_id,
            'season_id': self.season_id,

            # 'year': self.year,
            # 'aired': self.aired,
            # 'premiered': self.premiered,

            'rating': self.rating,

            'mediatype': 'season',

            # internally used for routing
            "mode": "episodes"
        }


# dto
class EpisodeData(ListableItem):
    """ A single Episode of a Season of a Series """

    def __init__(self, data: dict):
        super().__init__()
        from . import utils

        panel = data.get('panel') or data
        meta = panel.get("episode_metadata") or panel

        self.id = panel.get("id")
        self.title: str = utils.format_long_episode_title(meta.get("season_title"), meta.get("episode_number"),
                                                          panel.get("title"))
        self.tvshowtitle: str = meta.get("series_title", "")
        self.duration: int = int(meta.get("duration_ms", 0) / 1000)
        self.playhead: int = data.get("playhead", 0)
        self.season: int = meta.get("season_number", 1)
        self.episode: int = meta.get("episode", 1)
        self.episode_id: str | None = panel.get("id")
        self.season_id: str | None = meta.get("season_id")
        self.series_id: str | None = meta.get("series_id")
        self.plot: str = panel.get("description", "")
        self.plotoutline: str = panel.get("description", "")
        self.year: str = meta.get("episode_air_date")[:4] if meta.get("episode_air_date") is not None else ""
        self.aired: str = meta.get("episode_air_date")[:10] if meta.get("episode_air_date") is not None else ""
        self.premiered: str = meta.get("episode_air_date")[:10] if meta.get("episode_air_date") is not None else ""
        self.thumb: str | None = utils.get_img_from_struct(panel, "thumbnail", 2)
        self.fanart: str | None = utils.get_img_from_struct(panel, "thumbnail", 2)
        self.poster: str | None = None
        self.banner: str | None = None
        self.rating: int = 0
        self.playcount: int = 0
        self.stream_id: str | None = utils.get_stream_id_from_item(panel)

        self.recalc_playcount()

    def recalc_playcount(self):
        if self.playhead is not None and self.duration is not None:
            self.playcount = 1 if (int(self.playhead / self.duration * 100)) > 90 else 0

    def get_info(self, args: Args) -> Dict:
        return {
            'title': self.title,
            'tvshowtitle': self.tvshowtitle,
            'season': self.season,
            'episode': self.episode,
            'plot': self.plot,
            'plotoutline': self.plotoutline,

            'playhead': self.playhead,
            'duration': self.duration,
            'playcount': self.playcount,

            'season_id': self.season_id,
            'series_id': self.series_id,
            'episode_id': self.episode_id,
            'stream_id': self.stream_id,

            'year': self.year,
            'aired': self.aired,
            'premiered': self.premiered,

            'rating': self.rating,

            'mediatype': 'episode',

            # internally used for routing
            "mode": "videoplay"
        }


class MovieData(ListableItem):
    def __init__(self, data: dict):
        super().__init__()
        from . import utils

        panel = data.get('panel') or data
        meta = panel.get("movie_metadata") or panel

        self.id = panel.get("id")
        self.title: str = meta.get("movie_listing_title", "")
        self.tvshowtitle: str = meta.get("movie_listing_title", "")
        self.duration: int = int(meta.get("duration_ms", 0) / 1000)
        self.playhead: int = data.get("playhead", 0)
        self.season: int = 1
        self.episode: int = 1
        self.episode_id: str | None = panel.get("id")
        self.season_id: str | None = None
        self.series_id: str | None = None
        self.plot: str = panel.get("description", "")
        self.plotoutline: str = panel.get("description", "")
        self.year: str = meta.get("premium_available_date")[:10] if meta.get(
            "premium_available_date") is not None else ""
        self.aired: str = meta.get("premium_available_date")[:10] if meta.get(
            "premium_available_date") is not None else ""
        self.premiered: str = meta.get("premium_available_date")[:10] if meta.get(
            "premium_available_date") is not None else ""
        self.thumb: str | None = utils.get_img_from_struct(panel, "thumbnail", 2)
        self.fanart: str | None = utils.get_img_from_struct(panel, "thumbnail", 2)
        self.poster: str | None = None
        self.banner: str | None = None
        self.rating: int = 0
        self.playcount: int = 0
        self.stream_id: str | None = utils.get_stream_id_from_item(panel)

        self.recalc_playcount()

    def recalc_playcount(self):
        if self.playhead is not None and self.duration is not None:
            self.playcount = 1 if (int(self.playhead / self.duration * 100)) > 90 else 0

    def get_info(self, args: Args) -> Dict:
        return {
            'title': self.title,
            'tvshowtitle': self.tvshowtitle,
            'season': self.season,
            'episode': self.episode,
            'plot': self.plot,
            'plotoutline': self.plotoutline,

            'playhead': self.playhead,
            'duration': self.duration,
            'playcount': self.playcount,

            'series_id': self.series_id,
            'season_id': self.season_id,
            'episode_id': self.episode_id,
            'stream_id': self.stream_id,

            'year': self.year,
            'aired': self.aired,
            'premiered': self.premiered,

            'rating': self.rating,

            'mediatype': 'movie',

            # internally used for routing
            "mode": "videoplay"
        }


class CrunchyrollError(Exception):
    pass


class LoginError(Exception):
    pass
