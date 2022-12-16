#!/usr/bin/env python2
# -*- coding: utf-8 -*-

#---------------------------------------
#   Import Libraries
#---------------------------------------
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import json
import codecs

#---------------------------------------
#   [Required] Script Information
#---------------------------------------
ScriptName = 'SLCBTemplate'
Website = 'https://github.com/nossebro/SLCBTemplate'
Creator = 'nossebro'
Version = '0.0.3'
Description = 'Streamlabs Chatbot Template'

#---------------------------------------
#   Script Variables
#---------------------------------------
Logger = None
ScriptSettings = None
SettingsFile = os.path.join(os.path.dirname(__file__), "Settings.json")
UIConfigFile = os.path.join(os.path.dirname(__file__), "UI_Config.json")

#---------------------------------------
#   Script Classes
#---------------------------------------
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
			self.__dict__ = self.MergeSettings(defaults, settings)
		except:
			self.__dict__ = defaults

	def MergeSettings(self, x=dict(), y=dict()):
		z = x.copy()
		for attr in x:
			if attr in y:
				z[attr] = y[attr]
		return z

	def DefaultSettings(self, settingsfile=None):
		defaults = dict()
		with codecs.open(settingsfile, encoding="utf-8-sig", mode="r") as f:
			ui = json.load(f, encoding="utf-8")
		for key in ui:
			try:
				defaults[key] = ui[key]["value"]
			except:
				continue
		return defaults

	def Reload(self, jsondata):
		self.__dict__ = self.MergeSettings(self.DefaultSettings(UIConfigFile), json.loads(jsondata, encoding="utf-8"))
		self.SaveSettings(SettingsFile)

	def SaveSettings(self, settingsfile=None):
		defaults = self.DefaultSettings(UIConfigFile)
		self.__dict__ = self.MergeSettings(defaults, self.__dict__)
		try:
			with codecs.open(settingsfile, encoding="utf-8-sig", mode="w") as f:
				json.dump(self.__dict__, f, encoding="utf-8", indent=2)
			with codecs.open(settingsfile.replace("json", "js"), encoding="utf-8-sig", mode="w") as f:
				f.writelines("var settings = {0};".format(json.dumps(self.__dict__, encoding="utf-8", indent=2)))
		except:
			Parent.Log(ScriptName, "SaveSettings(): Could not write settings to file")

#---------------------------------------
#   Script Functions
#---------------------------------------
def GetLogger():
	log = logging.getLogger(ScriptName)
	log.setLevel(logging.DEBUG)

	sl = StreamlabsLogHandler()
	sl.setFormatter(logging.Formatter("%(funcName)s(): %(message)s"))
	sl.setLevel(logging.INFO)
	log.addHandler(sl)

	fl = TimedRotatingFileHandler(filename=os.path.join(os.path.dirname(__file__), "info"), when="w0", backupCount=8, encoding="utf-8")
	fl.suffix = "%Y%m%d"
	fl.setFormatter(logging.Formatter("%(asctime)s  %(funcName)s(): %(levelname)s: %(message)s"))
	fl.setLevel(logging.INFO)
	log.addHandler(fl)

	if ScriptSettings.DebugMode:
		dfl = TimedRotatingFileHandler(filename=os.path.join(os.path.dirname(__file__), "debug"), when="h", backupCount=24, encoding="utf-8")
		dfl.suffix = "%Y%m%d%H%M%S"
		dfl.setFormatter(logging.Formatter("%(asctime)s  %(funcName)s(): %(levelname)s: %(message)s"))
		dfl.setLevel(logging.DEBUG)
		log.addHandler(dfl)

	log.debug("Logger initialized")
	return log

#---------------------------------------
#   Chatbot Initialize Function
#---------------------------------------
def Init():
	global ScriptSettings
	ScriptSettings = Settings(SettingsFile)
	global Logger
	Logger = GetLogger()

#---------------------------------------
#   Chatbot Script Unload Function
#---------------------------------------
def Unload():
	global Logger
	if Logger:
		for handler in Logger.handlers[:]:
			Logger.removeHandler(handler)
		Logger = None

#---------------------------------------
#   Chatbot Save Settings Function
#---------------------------------------
def ReloadSettings(jsondata):
	global Logger
	ScriptSettings.Reload(jsondata)
	Parent.BroadcastWsEvent('{0}_UPDATE_SETTINGS'.format(ScriptName.upper()), json.dumps(ScriptSettings.__dict__))
	if Logger:
		Logger.debug("Settings reloaded")
		ScriptToggled(False)
		ScriptToggled(True)

#---------------------------------------
#   Chatbot Toggle Function
#---------------------------------------
def ScriptToggled(state):
	global Logger
	if state:
		if not Logger:
			Init()
		Logger.debug("Script toggled on")
	else:
		Logger.debug("Script toggled off")
		Unload()

#---------------------------------------
#   Chatbot Execute Function
#---------------------------------------
def Execute(data):
	global Logger
	if not Logger:
		return

#---------------------------------------
#   Chatbot Tick Function
#---------------------------------------
def Tick():
	global Logger
	if not Logger:
		return
