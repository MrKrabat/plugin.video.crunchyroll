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
import re
import sys

sys.modules['_asyncio'] = None  # @see: https://kodi.wiki/view/Python_Problems#asyncio

import xbmc
import xbmcaddon

# plugin constants
_addon = xbmcaddon.Addon(id=re.sub(r"^plugin://([^/]+)/.*$", r"\1", sys.argv[0]))
_plugin = _addon.getAddonInfo("name")
_version = _addon.getAddonInfo("version")

xbmc.log("[PLUGIN] %s: version %s initialized" % (_plugin, _version))

if __name__ == "__main__":
    from resources.lib import crunchyroll

    # start addon
    crunchyroll.main(sys.argv)
