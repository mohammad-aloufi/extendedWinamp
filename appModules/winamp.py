#appModules/winamp.py
#A part of NonVisual Desktop Access (NVDA)
#Copyright (C) 2006-2010 NVDA Contributors <http://www.nvda-project.org/>
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.

#Some features added by Hrvoje Katic <hrvojekatic@gmail.com>

from ctypes import *
from ctypes.wintypes import *
import winKernel
import winUser
from scriptHandler import isScriptWaiting
from NVDAObjects.IAccessible import IAccessible 
import appModuleHandler
import ui
import speech
import locale
import controlTypes
import api
import gui
import wx
import addonHandler
addonHandler.initTranslation()

# message used to sent many messages to winamp's main window. 
# most all of the IPC_* messages involve sending the message in the form of:
#   result = SendMessage(hwnd_winamp,WM_WA_IPC,(parameter),IPC_*);

WM_WA_IPC=winUser.WM_USER

# winamp window
IPC_GET_SHUFFLE=250
IPC_GET_REPEAT=251
IPC_SETVOLUME=122
IPC_SETPANNING=123
IPC_GETOUTPUTTIME=105
IPC_JUMPTOTIME=106

# playlist editor
IPC_PLAYLIST_GET_NEXT_SELECTED=3029
IPC_PE_GETCURINDEX=100
IPC_PE_GETINDEXTOTAL=101
# in_process ONLY
IPC_PE_GETINDEXTITLE=200 #  lParam = pointer to fileinfo2 structure

#Default values for review and alternate jump times
reviewTime=6
alternateJumpTime=5

#: A utility function for converting ms to hours/minutes/seconds
def sec2str(seconds, precision=0):
	hour=seconds//3600
	min=(seconds//60)%60
	sec=seconds-(hour*3600)-(min*60)
	sec_spec="."+str(precision)+"f"
	sec_string=sec.__format__(sec_spec)
	string=""
	if (hour==1):
		string+=_("%d hour, ")%hour
	elif (hour>=2):
		string+=_("%d hours, ")%hour
	if (min==1):
		string+=_("%d minute, ")%min
	elif (min>=2):
		string+=_("%d minutes, ")%min
	if (sec==1):
		string+=_("%s second")%sec_string
	else:
		string+=_("%s seconds")%sec_string
	return string

class fileinfo2(Structure):
	_fields_=[
		('fileindex',c_int),
		('filetitle',c_char*256),
		('filelength',c_char*16),
	]

class AppModule(appModuleHandler.AppModule):

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		windowClass = obj.windowClassName
		if windowClass == "Winamp PE":
			clsList.insert(0, winampPlaylistEditor)
		elif windowClass == "Winamp v1.x":
			clsList.insert(0, winampMainWindow)

	def getShuffle(self):
		return winUser.sendMessage(self.hwndWinamp,WM_WA_IPC,0,IPC_GET_SHUFFLE)

	def getRepeat(self):
		return winUser.sendMessage(self.hwndWinamp,WM_WA_IPC,0,IPC_GET_REPEAT)

	def getVolume(self):
		return winUser.sendMessage(self.hwndWinamp,WM_WA_IPC,-666,IPC_SETVOLUME)

	def setVolume(self,vol):
		return winUser.sendMessage(self.hwndWinamp,WM_WA_IPC,vol,IPC_SETVOLUME)

	def getPanning(self):
		return winUser.sendMessage(self.hwndWinamp,WM_WA_IPC,-666,IPC_SETPANNING)

	def setPanning(self,pan):
		return winUser.sendMessage(self.hwndWinamp,WM_WA_IPC,pan,IPC_SETPANNING)

	def getOutputTime(self,mode):
		return winUser.sendMessage(self.hwndWinamp,WM_WA_IPC,mode,IPC_GETOUTPUTTIME)

	def jumpToTime(self,ms):
		return winUser.sendMessage(self.hwndWinamp,WM_WA_IPC,ms,IPC_JUMPTOTIME)

	def __init__(self, *args, **kwargs):
		super(AppModule, self).__init__(*args, **kwargs)
		self.hwndWinamp=windll.user32.FindWindowA("Winamp v1.x",None)

class winampMainWindow(IAccessible):

	def event_nameChange(self):
		pass

	def script_shuffleToggle(self,gesture):
		gesture.send()
		if not isScriptWaiting():
			api.processPendingEvents()
			if self.appModule.getShuffle():
				onOff=_("on")
			else:
				onOff=_("off")
			ui.message(onOff)

	def script_repeatToggle(self,gesture):
		gesture.send()
		if not isScriptWaiting():
			api.processPendingEvents()
			if self.appModule.getRepeat():
				onOff=_("on")
			else:
				onOff=_("off")
			ui.message(onOff)

	def script_mute(self,gesture):
		self.appModule.setVolume(0)
		ui.message(_("mute"))
	script_mute.__doc__=_("Mute playback")

	def script_volume25(self,gesture):
		self.appModule.setVolume(64)
		ui.message("25%")
	script_volume25.__doc__=_("Set playback volume to 25%")

	def script_volume50(self,gesture):
		self.appModule.setVolume(128)
		ui.message("50%")
	script_volume50.__doc__=_("Set playback volume to 50%")

	def script_volume100(self,gesture):
		self.appModule.setVolume(255)
		ui.message("100%")
	script_volume100.__doc__=_("Set playback volume to 100%")

	def script_panLeft(self,gesture):
		self.appModule.setPanning(max(self.appModule.getPanning()-4, -127))
	script_panLeft.__doc__=_("Pan left")

	def script_panRight(self,gesture):
		self.appModule.setPanning(min(self.appModule.getPanning()+4, 127))
	script_panRight.__doc__=_("Pan right")

	def script_panCenter(self,gesture):
		self.appModule.setPanning(0)
		ui.message(_("center"))
	script_panCenter.__doc__=_("Pan center")

	def script_totalTrackLength(self,gesture):
		tm=self.appModule.getOutputTime(1)
		if tm==-1:
			return ui.message(_("No time information."))
		ui.message(sec2str(tm))
	script_totalTrackLength.__doc__=_("Speaks total track length")

	def script_trackTimeElapsed(self,gesture):
		tm=self.appModule.getOutputTime(0)/1000
		if tm==-1:
			return ui.message(_("No time information."))
		ui.message(sec2str(tm))
	script_trackTimeElapsed.__doc__=_("Speaks track elapsed time")

	def script_trackTimeRemaining(self,gesture):
		tm=self.appModule.getOutputTime(1)-self.appModule.getOutputTime(0)/1000
		if self.appModule.getOutputTime(1)==-1:
			return ui.message(_("No time information."))
		ui.message(sec2str(tm))
	script_trackTimeRemaining.__doc__=_("Speaks track remaining time")

	def script_reviewEndOfTrack(self,gesture):
		total=self.appModule.getOutputTime(2)
		review=total-reviewTime*1000
		if self.appModule.jumpToTime(review)==-1:
			ui.message(_("not playing"))
	script_reviewEndOfTrack.__doc__=_("Review the end of track (last 6 seconds by default)")

	def script_setReviewTime(self,gesture):
		def run():
			global reviewTime
			gui.mainFrame.prePopup()
			d=wx.TextEntryDialog(gui.mainFrame, _("Seconds:"), _("Set review time"))
			res=d.ShowModal()
			if res==wx.ID_OK:
				try: reviewTime=int(d.GetValue())
				except ValueError: wx.MessageBox(_("Bad value entered! Please try again."), _("Error"), wx.OK|wx.ICON_ERROR)
			gui.mainFrame.postPopup()
		wx.CallAfter(run)
	script_setReviewTime.__doc__=_("Set the review time (in seconds) for use with Review End of Track command")

	def script_alternateJumpForward(self,gesture):
		pos=self.appModule.getOutputTime(0)
		jump=pos+alternateJumpTime*1000
		if self.appModule.jumpToTime(jump)==-1:
			ui.message(_("not playing"))
	script_alternateJumpForward.__doc__=_("Alternate jump forward (6 seconds by default)")

	def script_alternateJumpBackward(self,gesture):
		pos=self.appModule.getOutputTime(0)
		jump=pos-alternateJumpTime*1000
		if self.appModule.jumpToTime(jump)==-1:
			ui.message(_("not playing"))
	script_alternateJumpBackward.__doc__=_("Alternate jump backward (6 seconds by default)")

	def script_setAlternateJumpTime(self,gesture):
		def run():
			global alternateJumpTime
			gui.mainFrame.prePopup()
			d=wx.TextEntryDialog(gui.mainFrame, _("Seconds:"), _("Set alternate jump time"))
			res=d.ShowModal()
			if res==wx.ID_OK:
				try: alternateJumpTime=int(d.GetValue())
				except ValueError: wx.MessageBox(_("Bad value entered! Please try again."), _("Error"), wx.OK|wx.ICON_ERROR)
			d.Destroy()
			gui.mainFrame.postPopup()
		wx.CallAfter(run)
	script_setAlternateJumpTime.__doc__=_("Set alternate jump time (in seconds)")

	__gestures = {
		"kb:s": "shuffleToggle",
		"kb:r": "repeatToggle",
		"kb:F5": "mute",
		"kb:F6": "volume25",
		"kb:F7": "volume50",
		"kb:F8": "volume100",
		"kb:Shift+LeftArrow": "panLeft",
		"kb:Shift+RightArrow": "panRight",
		"kb:Shift+UpArrow": "panCenter",
		"kb:Control+Shift+t": "totalTrackLength",
		"kb:Control+Shift+e": "trackTimeElapsed",
		"kb:Control+Shift+r": "trackTimeRemaining",
		"kb:Shift+r": "reviewEndOfTrack",
		"kb:Control+r": "setReviewTime",
		"kb:Shift+j": "setAlternateJumpTime",
		"kb:Control+RightArrow": "alternateJumpForward",
		"kb:Control+LeftArrow": "alternateJumpBackward",
	}

class winampPlaylistEditor(winampMainWindow):

	def _get_name(self):
		curIndex=winUser.sendMessage(self.appModule.hwndWinamp,WM_WA_IPC,-1,IPC_PLAYLIST_GET_NEXT_SELECTED)
		if curIndex <0:
			return None
		info=fileinfo2()
		info.fileindex=curIndex
		internalInfo=winKernel.virtualAllocEx(self.processHandle,None,sizeof(info),winKernel.MEM_COMMIT,winKernel.PAGE_READWRITE)
		winKernel.writeProcessMemory(self.processHandle,internalInfo,byref(info),sizeof(info),None)
		winUser.sendMessage(self.windowHandle,WM_WA_IPC,IPC_PE_GETINDEXTITLE,internalInfo)
		winKernel.readProcessMemory(self.processHandle,internalInfo,byref(info),sizeof(info),None)
		winKernel.virtualFreeEx(self.processHandle,internalInfo,0,winKernel.MEM_RELEASE)
		return unicode("%d.\t%s\t%s"%(curIndex+1,info.filetitle,info.filelength), errors="replace", encoding=locale.getlocale()[1])

	def _get_role(self):
		return controlTypes.ROLE_LISTITEM

	def script_changeItem(self,gesture):
		gesture.send()
		if not isScriptWaiting():
			api.processPendingEvents()
			speech.speakObject(self,reason=controlTypes.REASON_FOCUS)

	def event_nameChange(self):
		return super(winampMainWindow,self).event_nameChange()

	__changeItemGestures = (
		"kb:upArrow",
		"kb:downArrow",
		"kb:pageUp",
		"kb:pageDown",
	)

	def initOverlayClass(self):
		for gesture in self.__changeItemGestures:
			self.bindGesture(gesture, "changeItem")
