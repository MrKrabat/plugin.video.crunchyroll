import re
import xbmc
import xbmcaddon
from . import utils
from .client import CrunchyrollClient


def log(msg):
    xbmc.log(f"[Crunchyroll-Monitor] {msg}")


def run():
    monitor = xbmc.Monitor()

    addon = xbmcaddon.Addon(id=utils.ADDON_ID)
    email = addon.getSetting("crunchyroll_username")
    password = addon.getSetting("crunchyroll_password")
    locale = utils.local_from_id(addon.getSetting("subtitle_language"))
    sync_playtime = addon.getSetting("sync_playtime")
    page_size = addon.getSettingInt("page_size")
    resolution = addon.getSetting("resolution")
    cr = None

    while not monitor.abortRequested():

        player = xbmc.Player()
        if player.isPlayingVideo():
            # pylint: disable=E1101
            item = player.getPlayingItem()
            url = player.getPlayingFile()
            if re.search("crunchyroll.com", url):
                log("A crunchyroll video is being played")
                # Initialize client only on first video play
                if not cr:
                    cr = CrunchyrollClient(email, password, locale, page_size, resolution)
                if sync_playtime:
                    info_tag = item.getVideoInfoTag()
                    episode_id = info_tag.getOriginalTitle()
                    playhead = player.getTime()
                    cr.update_playhead(episode_id, int(playhead))
        else:
            log("Nothing is being played. Nothing to do")

        if monitor.waitForAbort(10):
            break
