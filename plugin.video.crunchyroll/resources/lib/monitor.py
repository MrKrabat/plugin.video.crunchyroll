import re
import xbmc
import xbmcaddon
from . import utils
from .client import CrunchyrollClient


def log(msg):
    xbmc.log(f"[Crunchyroll-Monitor] {msg}")


def run_crunchyroll_monitor():
    player = xbmc.Player()
    item = player.getPlayingItem()
    addon = xbmcaddon.Addon(id=utils.ADDON_ID)
    email = addon.getSetting("crunchyroll_username")
    password = addon.getSetting("crunchyroll_password")
    locale = utils.local_from_id(addon.getSetting("subtitle_language"))
    sync_playtime = addon.getSetting("sync_playtime")
    page_size = addon.getSettingInt("page_size")
    resolution = addon.getSetting("resolution")

    try:
        cr = CrunchyrollClient(email, password, locale, page_size, resolution)
    # pylint: disable=W0718
    except Exception as err:
        xbmc.log(f"{err=}", xbmc.LOGERROR)

    if sync_playtime:
        # E1128 due to mock
        # pylint: disable=E1128
        info_tag = item.getVideoInfoTag()
        episode_id = info_tag.getOriginalTitle()
        playhead = player.getTime()
        try:
            cr.update_playhead(episode_id, int(playhead))
        # pylint: disable=W0718
        except Exception as err:
            xbmc.log(f"{err=}", xbmc.LOGERROR)


def run():
    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        player = xbmc.Player()
        if player.isPlayingVideo():
            # pylint: disable=E1101
            url = player.getPlayingFile()
            if re.search("crunchyroll.com", url):
                log("A crunchyroll video is being played")
                run_crunchyroll_monitor()
        else:
            log("Nothing is being played. Nothing to do")

        if monitor.waitForAbort(10):
            break
