from datetime import datetime
import re
import xbmc
import xbmcgui
import xbmcaddon
from . import utils
from .client import CrunchyrollClient


class MonitorTask:

    def __init__(self, name, interval=1):
        self.interval = interval
        self.lastrun = int(datetime.now().timestamp())
        self.client = None
        self.name = name

    def should_run(self):
        now = int(datetime.now().timestamp())
        next_run = self.lastrun + self.interval
        should_run = now > next_run
        xbmc.log(f"[Crunchyroll-Monitor][Task {self.name}] Is now[{now}] > next_run[{next_run}]: {should_run}")
        return should_run

    def update_lastrun(self):
        self.lastrun = int(datetime.now().timestamp())

    def get_crunchyroll_client(self):
        if not self.client:
            addon = xbmcaddon.Addon(id=utils.ADDON_ID)
            email = addon.getSetting("crunchyroll_username")
            password = addon.getSetting("crunchyroll_password")
            settings = {
                "prefered_subtitle": utils.local_from_id(addon.getSetting("subtitle_language")),
                "prefered_audio": addon.getSetting("prefered_audio"),
                "page_size": addon.getSettingInt("page_size"),
                "resolution": int(addon.getSetting("resolution"))
            }

            try:
                self.client = CrunchyrollClient(email, password, settings)
            # pylint: disable=W0718
            except Exception as err:
                xbmc.log(f"[Crunchyroll-Monitor][Task {self.name}] {err=}", xbmc.LOGERROR)
        return self.client

    def is_playing_crunchyroll_video(self):
        player = xbmc.Player()
        if player.isPlayingVideo():
            # pylint: disable=E1101
            url = player.getPlayingFile()
            return re.search("crunchyroll", url)
        return False

    def _run(self, episode_id):
        pass

    def run(self):
        if self.is_playing_crunchyroll_video():
            xbmc.log(f"[Crunchyroll-Monitor][Task {self.name}] Running")
            player = xbmc.Player()
            item = player.getPlayingItem()
            # E1128 due to mock
            # pylint: disable=E1128
            info_tag = item.getVideoInfoTag()
            episode_id = info_tag.getOriginalTitle()
            self._run(episode_id)


class UpdatePlayhead(MonitorTask):
    def __init__(self):
        super().__init__("UpdatePlayhead", 10)

    def _run(self, episode_id):
        addon = xbmcaddon.Addon(id=utils.ADDON_ID)
        sync_playtime = addon.getSetting("sync_playtime")
        if sync_playtime:
            player = xbmc.Player()
            playhead = player.getTime()
            try:
                self.get_crunchyroll_client().update_playhead(episode_id, int(playhead))
            # pylint: disable=W0718
            except Exception as err:
                xbmc.log(f"[Crunchyroll-Monitor][Task {self.name}] {err=}", xbmc.LOGERROR)


class SkipEvent(MonitorTask):

    def __init__(self, event_id, skip_message):
        super().__init__(type(self).__name__, 1)
        self.event_id = event_id
        self.skip_message = skip_message

    def _run(self, episode_id):
        addon = xbmcaddon.Addon(id=utils.ADDON_ID)
        if addon.getSetting(f"skip_{self.event_id}"):
            player = xbmc.Player()
            playhead = int(player.getTime())
            try:
                skip_events = self.get_crunchyroll_client().get_episode_skip_events(episode_id)
                if self.event_id in skip_events.keys():
                    skip_event = skip_events[self.event_id]
                    xbmc.log(f"[Crunchyroll-Monitor][Task {self.name}] {skip_event['end']} > {playhead} > {skip_event['start']} ?")
                    if skip_event['end'] > playhead > skip_event['start']:
                        player.seekTime(int(skip_event['end']))
                        icon_url = addon.getAddonInfo("icon")
                        xbmcgui.Dialog().notification(self.skip_message, "", icon_url, 5000)
            # pylint: disable=W0718
            except Exception as err:
                xbmc.log(f"[Crunchyroll-Monitor] {err=}", xbmc.LOGERROR)


class SkipIntro(SkipEvent):
    def __init__(self):
        addon = xbmcaddon.Addon(id=utils.ADDON_ID)
        super().__init__("intro", addon.getLocalizedString(30080))


class SkipCredits(SkipEvent):
    def __init__(self):
        addon = xbmcaddon.Addon(id=utils.ADDON_ID)
        super().__init__("credits", addon.getLocalizedString(30081))


class SkipRecap(SkipEvent):
    def __init__(self):
        addon = xbmcaddon.Addon(id=utils.ADDON_ID)
        super().__init__("recap", addon.getLocalizedString(30082))


class SkipPreview(SkipEvent):
    def __init__(self):
        addon = xbmcaddon.Addon(id=utils.ADDON_ID)
        super().__init__("preview", addon.getLocalizedString(30083))


class MonitorTaskManager:

    def __init__(self):
        self.tasks = []

    def register_task(self, task):
        xbmc.log(f"[Crunchyroll-Monitor] Registering task {task.name}", xbmc.LOGDEBUG)
        self.tasks.append(task)

    def run_tasks(self):
        xbmc.log("[Crunchyroll-Monitor] Checking tasks to run", xbmc.LOGDEBUG)
        for task in self.tasks:
            if task.should_run():
                task.update_lastrun()
                task.run()


def run():
    monitor = xbmc.Monitor()
    task_manager = MonitorTaskManager()

    task_manager.register_task(UpdatePlayhead())
    task_manager.register_task(SkipIntro())
    task_manager.register_task(SkipCredits())
    task_manager.register_task(SkipPreview())
    task_manager.register_task(SkipRecap())

    xbmc.log("[Crunchyroll-Monitor] Starting monitoring", xbmc.LOGDEBUG)
    while not monitor.abortRequested():
        task_manager.run_tasks()
        if monitor.waitForAbort(1):
            break
