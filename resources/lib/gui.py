# -*- coding: utf-8 -*-
"""
    Copyright (C) 2017 Sebastian Golasch (plugin.video.netflix)
    Copyright (C) 2018 Caphm (original implementation module)
    Copyright (C) 2023 smirgol (adaption for plugin.video.crunchyroll)
    XML based dialogs

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""

import time

import xbmc
import xbmcgui

ACTION_PREVIOUS_MENU = 10
ACTION_PLAYER_STOP = 13
ACTION_NAV_BACK = 92
ACTION_NOOP = 999

CMD_CLOSE_DIALOG_BY_NOOP = 'AlarmClock(closedialog,Action(noop),{},silent)'


class SkipModalDialog(xbmcgui.WindowXMLDialog):
    """Dialog for skipping video parts (intro, [credits, recap], ...)"""

    def __init__(self, *args, **kwargs):
        self.seek_time = kwargs['seek_time']
        self.args = kwargs['args']
        self.api = kwargs['api']
        self.content_id = kwargs['content_id']
        self.label = kwargs['label']
        self.action_exit_keys_id = [ACTION_PREVIOUS_MENU,
                                    ACTION_PLAYER_STOP,
                                    ACTION_NAV_BACK,
                                    ACTION_NOOP]
        super().__init__(*args)

    def onInit(self):
        self.getControl(1000).setLabel(self.label) # noqa

    def onClick(self, control_id):
        from resources.lib.videoplayer import update_playhead
        if control_id == 1000:
            xbmc.Player().seekTime(self.seek_time)
            update_playhead(self.args, self.api, self.content_id, int(self.seek_time))
            self.close()

    def onAction(self, action):
        if action.getId() in self.action_exit_keys_id:
            self.close()


def _show_modal_dialog(dialog_class, xml_filename, **kwargs):
    dialog = dialog_class(xml_filename, kwargs.get('addon_path'), 'default', '1080i', **kwargs)
    minutes = kwargs.get('minutes', 0)
    seconds = kwargs.get('seconds', 0)
    if minutes > 0 or seconds > 0:
        # Bug in Kodi AlarmClock function, if only the seconds are passed
        # the time conversion inside the function multiply the seconds by 60
        if seconds > 59 and minutes == 0:
            alarm_time = time.strftime('%M:%S', time.gmtime(seconds))
        else:
            alarm_time = f'{minutes:02d}:{seconds:02d}'
        xbmc.executebuiltin(CMD_CLOSE_DIALOG_BY_NOOP.format(alarm_time))

    dialog.doModal()

    if hasattr(dialog, 'return_value'):
        return dialog.return_value
    return None
