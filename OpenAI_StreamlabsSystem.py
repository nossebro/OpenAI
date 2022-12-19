# ---------------------------------------
#   Import Libraries
# ---------------------------------------
import logging
from logging.handlers import TimedRotatingFileHandler
import re
import os
import codecs
import json

# ---------------------------------------
#   [Required] Script Information
# ---------------------------------------
ScriptName = "OpenAI"
Website = "https://github.com/nossebro/OpenAI"
Creator = "nossebro"
Version = "0.0.5"
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
        request = Parent.PostRequest(url, header, body, True)
        response = json.loads(request)
        Logger.debug(response["status"])
        if "status" in response and response["status"] == 200:
            data = json.loads(response["response"])
            Logger.debug(data)
            return data
        elif "error" in response:
            Logger.error(response["error"])
        else:
            Logger.error("Unknown error: {}".json.dumps(response, indent=4))
    except Exception as e:
        Logger.error(e)


def OpenAIGetResponse(prompt, user):
    global ScriptSettings
    Body = {
        "model": ScriptSettings.OpenAIModel,
        "prompt": prompt,
        "temperature": ScriptSettings.OpenAITemperature,
        "max_tokens": int(ScriptSettings.OpenAIMaxToken),
        "top_p": ScriptSettings.OpenAITopP,
        "frequency_penalty": ScriptSettings.OpenAIFrequencyPenalty,
        "presence_penalty": ScriptSettings.OpenAIPresencePenalty,
        "user": user
    }
    result = OpenAIAPIPostRequest(
        "https://api.openai.com/v1/completions", body=Body)
    return result


def OpenAIGetModeration(prompt):
    global ScriptSettings
    Body = {
        "input": prompt
    }
    result = OpenAIAPIPostRequest(
        "https://api.openai.com/v1/moderations", body=Body)
    return result


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
    if data.IsFromDiscord():
        Logger.debug("Discord: {0}".format(data.Message))
        Parent.SendDiscordMessage("I received: {0}".format(data.Message))
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
        if not ScriptSettings.Command and data.GetParam(0).lower() != "@{0}".format(ScriptSettings.BotName.lower()):
            return
        if ScriptSettings.Command and data.GetParam(0).lower() != "!{0}".format(ScriptSettings.Command.lower()):
            return
        if Parent.IsOnCooldown(ScriptName, "ChatBot"):
            Logger.debug("{0}: Chatbot is on cooldown: {1}".format(
                ScriptSettings.BotName, Parent.GetCooldownDuration(ScriptName, "ChatBot")))
            return
        if Level < ScriptSettings.ChatBotLevel and not Name in ScriptSettings.ChatBotAllowlist.split(", "):
            Logger.debug("{0}: {1} has not enough permission to chat with bot".format(
                ScriptSettings.BotName, Name))
            return

        Message = re.sub(r"^@" + ScriptSettings.BotName + r"|^!" + ScriptSettings.Command + " ", "",
                         data.Message, flags=re.IGNORECASE).strip()
        if Message != "":
            Logger.debug("Send to AI from {0}: '{1}'".format(Name, Message))
            Mod = OpenAIGetModeration(Message.decode("unicode-escape"))
            if Mod and "results" in Mod:
                if Mod["results"][0]["flagged"]:
                    Logger.debug("{0}: User {1} send a flagged message: {2}".format(
                        ScriptName.BotName, Name, Message))
                    return
            Bot = OpenAIGetResponse(Message.decode("unicode-escape"), Name.decode("unicode-escape"))
            if Bot and "choices" in Bot:
                Parent.SendStreamMessage(
                    "@{0} {1}".format(Name, Bot["choices"][0]["text"].replace("\n", " ").strip()))
                Parent.AddCooldown(ScriptName, "ChatBot",
                                   ScriptSettings.ChatBotCooldown)
            else:
                Logger.debug("{0}: No response to message: {1}: {2}".format(
                    ScriptSettings.BotName, Message, json.dumps(Bot, indent=4)))

# ---------------------------------------
#   Chatbot Tick Function
# ---------------------------------------


def Tick():
    pass
