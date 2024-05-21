# -*- coding: utf-8 -*-
# Crunchyroll
# Copyright (C) 2024 Xtero
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
import xbmc
# pylint: disable=E0401
from resources.lib import main
from resources.lib import script

if "process_errors" not in locals():
    # pylint: disable=C0103
    process_errors = True

if __name__ == "__main__":
    url = sys.argv[0]
    xbmc.log(f"[Crunchyroll] {url}", xbmc.LOGDEBUG)
    if url == "main.py":
        # handling script call
        method = sys.argv[1]
        xbmc.log(f"[Crunchyroll] Script {method}")
        if method == "clear_subtitles_cache":
            script.clear_subtitles_cache()
        elif method == "clear_auth_cache":
            script.clear_auth_cache()
    else:
        # start addon
        xbmc.log("[Crunchyroll] running plugin")
        main.run(process_errors=process_errors)
