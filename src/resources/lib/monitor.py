import xbmc
import re
import xbmcaddon
from . import utils
from .client import CrunchyrollClient
import urllib.parse as urlparse
from urllib.parse import parse_qs

addon = xbmcaddon.Addon(id=utils.ADDON_ID)
email = addon.getSetting("crunchyroll_username")
password = addon.getSetting("crunchyroll_password")
locale = utils.local_from_id(addon.getSetting("subtitle_language"))
cr=None

def log(msg):
    xbmc.log(f"[Crunchyroll-Monitor] {msg}")

def run():
    monitor = xbmc.Monitor()
    global cr

    while not monitor.abortRequested():

        player = xbmc.Player()
        if player.isPlayingVideo():
            item = player.getPlayingItem()
            url = player.getPlayingFile()
            log(f"{url}")
            if re.search("crunchyroll.com", url):
                # Initialize client only on first video play
                if not cr:
                    cr = CrunchyrollClient(email, password, locale) 
                infoTag = item.getVideoInfoTag()
                episode_id = infoTag.getOriginalTitle()
                playhead = player.getTime()
                log(f"Updating episode {episode_id}  playhead with {playhead}")
                cr.update_playhead(episode_id, int(playhead))
        else:
            log("Nothing is being played")

        if monitor.waitForAbort(10):
            break
