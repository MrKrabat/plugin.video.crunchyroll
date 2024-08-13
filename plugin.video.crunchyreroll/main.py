# -*- coding: utf-8 -*-
# ${LICENSE_HEADER}

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
