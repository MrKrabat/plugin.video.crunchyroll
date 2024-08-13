# pylint: skip-file
import logging
import json
import xbmc
import xbmcgui
from xbmcgui import Dialog
from addondev import support

logger = logging.getLogger("MOCK")


def mock_executeJSONRPC(jsonrpccommand):
    ret = {
        "result": {}
    }
    logger.debug(f"command:{jsonrpccommand}")
    command = json.loads(jsonrpccommand)
    if command.get('method', '') == "Settings.GetSettingValue":
        if command.get('params', {}).get('settings', '') == "network.usehttpproxy":
            logger.debug("Try to return httpproxy")
            ret['result']['value'] = False
    if command.get('method', '') == "Addons.GetAddonDetails":
        if command.get('params', {}).get("addonid", "") == "inputstream.adaptive":
            if "enabled" in command.get('params', {}).get("properties", []):
                ret["result"]["addon"] = {"enabled": True}
    return json.dumps(ret)


def mock_getCondVisibility(condition):
    logger.debug("In the test context, we will hide everything")
    return False


def mock_getInfoLabel(label):
    if label == "System.BuildVersion":
        return "20.2.0.0"
    elif label == "System.OSVersionInfo":
        return "Linux (kernel: 5.15.133.1-microsoft-standard-WSL2)"
    return False


def mock_yesno_dialog(heading='', message='', nolabel=None, yeslabel=None, autoclose=0):
    return False


class DialogFixed(Dialog):
    def yesno(self, heading, message, nolabel='', yeslabel='', autoclose=0):
        super().yesno(heading, line1=message, nolabel=nolabel, yeslabel=yeslabel, autoclose=autoclose)


class DataPipe:
    def __init_(self):
        self.msg = ""

    def send(self, data):
        self.msg = data.get("prompt")

    def recv(self):
        return "no"


support.data_pipe = DataPipe()
support.kodi_paths['xbmcbin'] = "dummy"
xbmc.executeJSONRPC = mock_executeJSONRPC
xbmc.getCondVisibility = mock_getCondVisibility
xbmc.getInfoLabel = mock_getInfoLabel
xbmcgui.Dialog = DialogFixed
