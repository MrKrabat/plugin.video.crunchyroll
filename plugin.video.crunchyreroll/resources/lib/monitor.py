# -*- coding: utf-8 -*-
# ${LICENSE_HEADER}

import traceback
from datetime import datetime
from time import sleep
import threading
import re
import xbmc
import xbmcgui
import xbmcaddon
from . import utils
from . import main


class CrunchyrollTask():

    def error(self, msg):
        xbmc.log(f"[CrunchyrollTask][Task {self.name}] {msg}", xbmc.LOGERROR)

    def debug(self, msg):
        xbmc.log(f"[CrunchyrollTask][Task {self.name}] {msg}", xbmc.LOGDEBUG)

    def __init__(self):
        self.name = type(self).__name__

    def _run(self, episode_id):
        pass

    def run(self):
        self.debug("Running")
        player = xbmc.Player()
        try:
            if player.isPlaying():
                # E1128 due to mock
                # pylint: disable=E1128
                episode_id = player.getPlayingItem().getProperty('episode_id')
                self._run(episode_id)
        except Exception as err:
            self.error(f"{err=}")
            self.error(f"{traceback.format_exc()}")


class UpdatePlayhead(CrunchyrollTask):
    def _run(self, episode_id):
        addon = xbmcaddon.Addon(id=utils.ADDON_ID)
        sync_playtime = addon.getSettingBool("sync_playtime")
        if sync_playtime:
            player = xbmc.Player()
            playhead = player.getTime()
            client = utils.init_crunchyroll_client()
            client.update_playhead(episode_id, int(playhead))


class SkipEvent(CrunchyrollTask):
    def __init__(self, event_id, localization):
        self.event_id = event_id
        self.localization = localization
        self.check_skip = True
        super().__init__()

    def _run(self, episode_id):
        addon = xbmcaddon.Addon(id=utils.ADDON_ID)
        if addon.getSettingBool(f"skip_{self.event_id}") and self.check_skip:
            player = xbmc.Player()
            playhead = int(player.getTime())
            client = utils.init_crunchyroll_client()
            skip_events = client.get_episode_skip_events(episode_id)
            # We may not have skip event
            if self.event_id in list(skip_events.keys()):
                skip_event = skip_events[self.event_id]
                # The object might exist and still be empty
                if 'end' in skip_event and 'start' in skip_event:
                    # Are we in the right time range to trigger the modal ?
                    if int(skip_event['end']) > playhead > int(skip_event['start']):
                        # If the modal have been shown, we never show it again during this episode
                        self.check_skip = False
                        if xbmcgui.Dialog().yesno(self.localization['question'], f"{addon.getLocalizedString(30086)} ?", autoclose=10000):
                            player.seekTime(int(skip_event['end']))
                            icon_url = addon.getAddonInfo("icon")
                            xbmcgui.Dialog().notification(self.localization['event'], "", icon_url, 5000)


class SkipIntro(SkipEvent):
    def __init__(self):
        addon = xbmcaddon.Addon(id=utils.ADDON_ID)
        localization = {
            "question":  addon.getLocalizedString(30076),
            "event": addon.getLocalizedString(30080)
        }
        super().__init__("intro", localization)


class SkipCredits(SkipEvent):
    def __init__(self):
        addon = xbmcaddon.Addon(id=utils.ADDON_ID)
        localization = {
            "question":  addon.getLocalizedString(30077),
            "event": addon.getLocalizedString(30081)
        }
        super().__init__("credits", localization)


class SkipRecap(SkipEvent):
    def __init__(self):
        addon = xbmcaddon.Addon(id=utils.ADDON_ID)
        localization = {
            "question":  addon.getLocalizedString(30078),
            "event": addon.getLocalizedString(30082)
        }
        super().__init__("recap", localization)


class SkipPreview(SkipEvent):
    def __init__(self):
        addon = xbmcaddon.Addon(id=utils.ADDON_ID)
        localization = {
            "question":  addon.getLocalizedString(30079),
            "event": addon.getLocalizedString(30083)
        }
        super().__init__("preview", localization)


class CrunchyrollVideoHandler:
    def error(self, msg):
        xbmc.log(f"[CrunchyrollVideoHandler] {msg}", xbmc.LOGERROR)

    def debug(self, msg):
        xbmc.log(f"[CrunchyrollVideoHandler] {msg}", xbmc.LOGDEBUG)

    def __init__(self, player, event):
        self.tasks = []
        self.seek_time = 0
        self.player = player
        self.stop_event = event
        self.episode_id = None
        self.init()
        self.run()
        self.stop()

    def init(self):
        # E1128 due to mock
        # pylint: disable=E1128
        self.episode_id = self.player.getPlayingItem().getProperty('episode_id')
        self.set_subtitles()
        self._register_task(UpdatePlayhead(), 10)
        self._register_task(SkipIntro(), 1)
        self._register_task(SkipCredits(), 1)
        self._register_task(SkipPreview(), 1)
        self._register_task(SkipRecap(), 1)

    def run(self):
        while not self.stop_event.is_set():
            try:
                if self.player.isPlaying():
                    self._run_tasks()
                    self.seek_time = self.player.getTime()
            except RuntimeError:
                self.debug("I'm still trying to get playtime info although there is nothing playing :(")
            sleep(1)

    def stop(self):
        self.set_playhead()

    def set_subtitles(self):
        addon = xbmcaddon.Addon(id=utils.ADDON_ID)
        prefered_subtitle = utils.sub_locale_from_id(addon.getSettingInt("subtitle_language"))
        actual_audio = self.player.getPlayingItem().getProperty("audio_language")
        if actual_audio == prefered_subtitle:
            self.debug("Disabling subtitle")
            self.player.showSubtitles(False)
        else:
            self.debug("Enabling subtitle")
            self.player.showSubtitles(True)
            subtitle_stream_id = 0
            subtitles = self.player.getAvailableSubtitleStreams()
            for idx, sub in enumerate(subtitles):
                if prefered_subtitle == sub:
                    subtitle_stream_id = idx
            self.debug(f"Selecting subtitle stream {subtitle_stream_id}")
            self.player.setSubtitleStream(subtitle_stream_id)

    def set_playhead(self):
        try:
            addon = xbmcaddon.Addon(id=utils.ADDON_ID)
            sync_playtime = addon.getSettingBool("sync_playtime")
            if sync_playtime:
                playhead = self.seek_time
                client = utils.init_crunchyroll_client()
                client.update_playhead(self.episode_id, int(playhead))
        except Exception as err:
            self.error(f"{err=}")
            self.error(f"{traceback.format_exc()}")

    def should_run_task(self, task_info):
        now = int(datetime.now().timestamp())
        next_run = task_info['lastrun'] + task_info['interval']
        should_run = now > next_run
        return should_run

    def _register_task(self, task, interval):
        self.debug(f"Registering task {task.name}")
        self.tasks.append({
            "task": task,
            "interval": interval,
            "lastrun": int(datetime.now().timestamp())
        })

    def _run_tasks(self):
        self.debug("Checking tasks to run")
        for task_info in self.tasks:
            if self.should_run_task(task_info):
                task_info['lastrun'] = int(datetime.now().timestamp())
                task_info['task'].run()


class CrunchyrollPlayer(xbmc.Player):
    def __init__(self):
        self.stop_event = None

    # pylint: disable=C0103
    def onAVStarted(self):
        url = self.getPlayingFile()
        xbmc.log(f"[CrunchyrollPlayer] url:{url}", xbmc.LOGDEBUG)
        if re.search("crunchyroll", url):
            xbmc.log("[CrunchyrollPlayer] starting thread", xbmc.LOGDEBUG)
            self.stop_event = threading.Event()
            thread = threading.Thread(target=CrunchyrollVideoHandler, args=[self, self.stop_event], daemon=True)
            thread.start()

    # pylint: disable=C0103
    def onPlayBackStopped(self):
        if self.stop_event:
            xbmc.log("[CrunchyrollPlayer] stopping thread", xbmc.LOGDEBUG)
            self.stop_event.set()
            self.stop_event = None

    # pylint: disable=C0103
    def onPlayBackEnded(self):
        addon = xbmcaddon.Addon(id=utils.ADDON_ID)
        if addon.getSettingBool("binge_watch"):
            playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            episode_id = playlist[-1].getProperty('episode_id')
            client = utils.init_crunchyroll_client()
            next_episode = client.get_next_episode(episode_id)
            if next_episode:
                item = main.play_episode(None, next_episode.id)
                url = item.path
                self.play(url, item.listitem)
        if self.stop_event:
            xbmc.log("[CrunchyrollPlayer] stopping thread", xbmc.LOGDEBUG)
            self.stop_event.set()
            self.stop_event = None


def run():
    monitor = xbmc.Monitor()
    # pylint: disable=W0612
    player = CrunchyrollPlayer() # noqa = F841
    xbmc.log("[Crunchyroll-Monitor] Starting monitoring", xbmc.LOGDEBUG)
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break
