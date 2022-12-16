# ---------------------------------------
#   Import Libraries
# ---------------------------------------
import logging
from logging.handlers import TimedRotatingFileHandler
import re
import os
import codecs
import json
import urllib

# ---------------------------------------
#   [Required] Script Information
# ---------------------------------------
ScriptName = "OpenAI"
Website = "https://github.com/nossebro/OpenAI"
Creator = "nossebro"
Version = "0.0.2"
Description = "OpenAI chat bot integration"

# ---------------------------------------
#   Script Variables
# ---------------------------------------
ScriptSettings = None
Logger = None
SettingsFile = os.path.join(os.path.dirname(__file__), "Settings.json")
UIConfigFile = os.path.join(os.path.dirname(__file__), "UI_Config.json")
APIKeyFile = os.path.join(os.path.dirname(__file__), "API_Key.js")

# ---------------------------------------
#   Script Classes
# ---------------------------------------


class StreamlabsLogHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            message = self.format(record)
            Parent.Log(ScriptName, message)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class Settings(object):
    def __init__(self, settingsfile=None):
        defaults = self.DefaultSettings(UIConfigFile)
        try:
            with codecs.open(settingsfile, encoding="utf-8-sig", mode="r") as f:
                settings = json.load(f, encoding="utf-8")
            self.__dict__ = MergeLists(defaults, settings)
        except:
            self.__dict__ = defaults

    def DefaultSettings(self, settingsfile=None):
        defaults = dict()
        with codecs.open(settingsfile, encoding="utf-8-sig", mode="r") as f:
            ui = json.load(f, encoding="utf-8")
        for key in ui:
            try:
                defaults[key] = ui[key]['value']
            except:
                if key != "output_file":
                    Parent.Log(
                        ScriptName, "DefaultSettings(): Could not find key {0} in settings".format(key))
        return defaults

    def Reload(self, jsondata):
        self.__dict__ = MergeLists(self.DefaultSettings(
            UIConfigFile), json.loads(jsondata, encoding="utf-8"))

# ---------------------------------------
#   Script Functions
# ---------------------------------------


def GetLogger():
    log = logging.getLogger(ScriptName)
    log.setLevel(logging.DEBUG)

    sl = StreamlabsLogHandler()
    sl.setFormatter(logging.Formatter("%(funcName)s(): %(message)s"))
    sl.setLevel(logging.INFO)
    log.addHandler(sl)

    fl = TimedRotatingFileHandler(filename=os.path.join(os.path.dirname(
        __file__), "info"), when="w0", backupCount=8, encoding="utf-8")
    fl.suffix = "%Y%m%d"
    fl.setFormatter(logging.Formatter(
        "%(asctime)s  %(funcName)s(): %(levelname)s: %(message)s"))
    fl.setLevel(logging.INFO)
    log.addHandler(fl)

    if ScriptSettings.DebugMode:
        dfl = TimedRotatingFileHandler(filename=os.path.join(os.path.dirname(
            __file__), "debug"), when="h", backupCount=24, encoding="utf-8")
        dfl.suffix = "%Y%m%d%H%M%S"
        dfl.setFormatter(logging.Formatter(
            "%(asctime)s  %(funcName)s(): %(levelname)s: %(message)s"))
        dfl.setLevel(logging.DEBUG)
        log.addHandler(dfl)

    log.debug("Logger initialized")
    return log


def MergeLists(x=dict(), y=dict()):
    z = dict()
    for attr in x:
        if attr not in y:
            z[attr] = x[attr]
        else:
            z[attr] = y[attr]
    return z


def OpenAIAPIPostRequest(url, header=dict(), body=dict()):
    global ScriptSettings
    header["Authorization"] = "Bearer {}".format(ScriptSettings.OpenAIAPIToken)
    Logger.debug(
        "Parent.PostRequest({}, {}, {}, {}".format(url, header, body, True))
    try:
        result = json.loads(Parent.PostRequest(url, header, body, True))
        Logger.debug(json.dumps(result, indent=4))
        if "status" in result and result["status"] == 200:
            return result
        elif "error" in result:
            Logger.error(result["error"])
        else:
            Logger.error("Unknown error: {}".json.dumps(result, indent=4))
    except Exception as e:
        Logger.error(e)


def OpenAIGetResponse(prompt):
    global ScriptSettings
    Body = {
        "model": ScriptSettings.OpenAIModel,
        "prompt": prompt,
        "temperature": ScriptSettings.OpenAITemperature,
        "max_tokens": int(ScriptSettings.OpenAIMaxToken),
        "top_p": ScriptSettings.OpenAITopP,
        "frequency_penalty": ScriptSettings.OpenAIFrequencyPenalty,
        "presence_penalty": ScriptSettings.OpenAIPresencePenalty
    }
    Logger.debug(json.dumps(Body, indent=4))
    result = OpenAIAPIPostRequest("https://api.openai.com/v1/completions", body=Body)
    if result:
        response = json.loads(result["response"])
        Logger.debug(json.dumps(response, indent=4))
        return response


# ---------------------------------------
#   Chatbot Initialize Function
# ---------------------------------------
def Init():
    global ScriptSettings
    ScriptSettings = Settings(SettingsFile)
    global Logger
    Logger = GetLogger()
    Logger.debug(json.dumps(ScriptSettings.__dict__))

# ---------------------------------------
#   Chatbot Script Unload Function
# ---------------------------------------


def Unload():
    global Logger
    if Logger:
        for handler in Logger.handlers[:]:
            Logger.removeHandler(handler)
        Logger = None

# ---------------------------------------
#   Chatbot Save Settings Function
# ---------------------------------------


def ReloadSettings(jsondata):
    ScriptSettings.Reload(jsondata)
    Logger.debug("Settings reloaded")
    Parent.BroadcastWsEvent('{0}_UPDATE_SETTINGS'.format(
        ScriptName.upper()), json.dumps(ScriptSettings.__dict__))
    Logger.debug(json.dumps(ScriptSettings.__dict__))

# ---------------------------------------
#   Chatbot Execute Function
# ---------------------------------------


def Execute(data):
    if data.IsChatMessage() and data.IsFromTwitch():
        Level = 0
        if Parent.HasPermission(data.User, "caster", ""):
            Level = 4
        elif Parent.HasPermission(data.User, "moderator", ""):
            Level = 3
        elif Parent.HasPermission(data.User, "subscriber", ""):
            Level = 2
        elif Parent.HasPermission(data.User, "regular", ""):
            Level = 1
        Name = data.UserName
        if not ScriptSettings.Command and data.GetParam(0) != "@{0}".format(ScriptSettings.BotName):
#            Logger.debug("{0}: Message not addressed to bot: {1}".format(ScriptSettings.BotName, data.Message))
            return
        if ScriptSettings.Command and data.GetParam(0) != "!{0}".format(ScriptSettings.Command):
#            Logger.debug("{0}: Message command not for bot: {1}".format(ScriptSettings.BotName, data.Message))
            return
        if Parent.IsOnCooldown(ScriptName, "ChatBot"):
            Logger.debug("{0}: Chatbot is on cooldown".format(
                ScriptSettings.BotName))
            return
        if Level < ScriptSettings.ChatBotLevel and not Name in ScriptSettings.ChatBotAllowlist.split(", "):
            Logger.debug("{0}: {1} has not enough permission to chat with bot".format(
                ScriptSettings.BotName, Name))
            return

        Message = re.sub(r"^@" + ScriptSettings.BotName, "",
                         data.Message, flags=re.IGNORECASE).strip()
        if Message != "":
            Logger.debug("Send to AI from {0}: '{1}'".format(Name, Message))
            Bot = OpenAIGetResponse(urllib.quote_plus(Message, ""))
            if Bot and "choices" in Bot:
                Parent.SendStreamMessage(
                    "@{0} {1}".format(Name, Bot["choices"][0]["text"].strip()))
                Parent.AddCooldown(ScriptName, "ChatBot", ScriptSettings.ChatBotCooldown)
            else:
                Logger.debug("{0}: No response to message: {1}: {2}".format(
                    ScriptSettings.BotName, Message, json.dumps(Bot, indent=4)))

# ---------------------------------------
#   Chatbot Tick Function
# ---------------------------------------


def Tick():
    pass
