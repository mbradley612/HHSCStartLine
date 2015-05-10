'''
Created on 23 Jan 2014

@author: MBradley
'''
from screenui.raceview import StartLineFrame,AddFleetDialog
from model.race import RaceManager
from screenui.audio import AudioManager
from persistence.recovery import RaceRecoveryManager
from lightsui.hardware import LIGHT_OFF, LIGHT_ON

import threading 
import logging
import sys

import datetime
import tkMessageBox
import Tkinter
import Queue
import ConfigParser
import os
import pickle




#
# LightsController uses the EasyDaqUSBRelay to control the hardware lights. It refreshes the lights every
# 500 milliseconds until all fleets have started. 
#
class LightsController():
    
    def __init__(self, tkRoot,easyDaqRelay,raceManager):
        self.tkRoot = tkRoot
        self.easyDaqRelay = easyDaqRelay
        self.raceManager = raceManager
        # we start assuming that our lights are off
        self.currentLights = [LIGHT_OFF, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF]
        self.wireController()
        
        self.updateTimer = None
        
    def wireController(self):
        
        
        self.raceManager.changed.connect("generalRecall",self.handleGeneralRecall)
        self.raceManager.changed.connect("sequenceStartedWithWarning",self.handleSequenceStarted)
        self.raceManager.changed.connect("sequenceStartedWithoutWarning",self.handleSequenceStarted)
        self.raceManager.changed.connect("startSequenceReset",self.handleStartSequenceReset)
        
        
        
    
    def handleGeneralRecall(self,fleet):
        self.cancelUpdateTimer()
        self.updateLights()
    
    def handleSequenceStarted(self):
        self.cancelUpdateTimer()
        self.updateLights()
        
    def handleStartSequenceReset(self):
        self.cancelUpdateTimer()
        self.updateLights()
        
    def cancelUpdateTimer(self):
        # if we have an update timer, cancel it. Note that if the update timer
        # has has already executed, the cancel has no effect and does not fail.
        if self.updateTimer:
            self.tkRoot.after_cancel(self.updateTimer)
        
    
    def calculateLightsDisplay(self):
        #
        # out default is no lights
        lights = [LIGHT_OFF, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF]
        
        # ask for the next fleet to start
        nextFleetToStart = self.raceManager.nextFleetToStart()
        
        # if we have a fleet to start
        if nextFleetToStart:
            secondsToStart = -1 * nextFleetToStart.adjustedDeltaSecondsToStartTime()
            
            if secondsToStart <=300 and secondsToStart > 240:
                lights = [LIGHT_ON, LIGHT_ON, LIGHT_ON, LIGHT_ON, LIGHT_ON]
            elif secondsToStart <= 240 and secondsToStart > 180:
                lights = [LIGHT_ON, LIGHT_ON, LIGHT_ON, LIGHT_ON, LIGHT_OFF]
            elif secondsToStart <= 180 and secondsToStart > 120: 
                lights = [LIGHT_ON, LIGHT_ON, LIGHT_ON, LIGHT_OFF, LIGHT_OFF]
            elif secondsToStart <= 120 and secondsToStart > 60: 
                lights = [LIGHT_ON, LIGHT_ON, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF]
            elif secondsToStart <= 60 and secondsToStart > 30: 
                lights = [LIGHT_ON, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF]
            elif secondsToStart <= 30 and (int(secondsToStart * 2) % 2 == 0):
                lights = [LIGHT_ON, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF]
            else:
                lights = [LIGHT_OFF, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF]
            
        return lights
    
    
                 
    
    def updateLights(self):
        
        newLights = self.calculateLightsDisplay()
        
        if newLights != self.currentLights:
            self.easyDaqRelay.sendRelayCommand(newLights)
            self.currentLights = newLights
        
        # check that we still have a fleet to start, if so,
        # calculate the time until our next change
        
        if self.raceManager.nextFleetToStart():
            # make sure we update idle tasks so that the screen updates. This is particularly important in speedy mode
            self.tkRoot.update_idletasks()
            
            self.updateTimer = self.tkRoot.after(500, self.updateLights)
            
        # if we don't have a race to start any more, set our lights to 0 and don't update ourselves again
        else:
            self.easyDaqRelay.sendRelayCommand([LIGHT_OFF, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF])
        
           
        
    def start(self):
        self.easyDaqRelay.start()     
                
    
    
        
    
    

#
# GunController uses the AudioManager to play a Wav file as the race "gun".
# It does this in response to events from the race manager when races change
# during the start sequence or when boats finish. It uses the Tk root
# to provide an event scheduler. 
#
class GunController():
    
    def __init__(self, tkRoot, audioManager, raceManager):
        self.tkRoot = tkRoot
        self.audioManager = audioManager
        self.raceManager = raceManager
        self.scheduledGuns = []
        self.wireController()
        
    #
    # We wire the controller by registering with the race manager
    # for the events we are interested in
    #   
    def wireController(self):
        self.raceManager.changed.connect("sequenceStartedWithWarning",self.handleSequenceStartedWithWarning)
        self.raceManager.changed.connect("sequenceStartedWithoutWarning",self.handleSequenceStartedWithoutWarning)
        self.raceManager.changed.connect("generalRecall",self.handleGeneralRecall)
        self.raceManager.changed.connect("startSequenceReset",self.handleStartSequenceReset)
        self.raceManager.changed.connect("finishAdded", self.handleFinishAdded)
        
        
    def fireGun(self):
        self.audioManager.queueClip("gun")
        
 
    def soundWarning(self):
        self.audioManager.queueClip("warning")
    
    #
    # millis is the time of the gun. The warning beeps are for the ten secoonds prior to the gun
    #
    def scheduleWarningBeeps(self,gunMillis,finalWarning=False):
        for warningMillis in range(gunMillis-10000, gunMillis, 1000):
            self.addSchedule(self.tkRoot.after(warningMillis, self.soundWarning))
        # if we give a final warning instead of a gun, schedule this
        if finalWarning:
            self.addSchedule(self.tkRoot.after(gunMillis, self.soundWarning))
    
 
    def scheduleGun(self,millis):
        logging.log(logging.DEBUG,"Scheduling gun for %d " % millis)
        scheduleId = self.tkRoot.after(millis, self.fireGun)
        
        self.addSchedule(scheduleId)
        
    def addSchedule(self,scheduleId):
        self.scheduledGuns.append(scheduleId)
        
    def cancelSchedules(self):
        for aSchedule in self.scheduledGuns:
            self.tkRoot.after_cancel(aSchedule)
        self.scheduledGuns = []
    
    
        
    def scheduleGunForFleetStart(self,aFleet, secondsBefore):
        # calculate seconds to start of fleet
        # convert negative seconds to start to positive 
        secondsToStart = aFleet.deltaSecondsToStartTime()  * -1
        
        
        # check that the fleet is still in the future (for example if we are debugging)
        if secondsToStart > 0:
            
            #
            # to calculate the seconds to gun, we take the seconds to start 
            # and subtract the requested seconds before divided by the test speed ratio.
            #
            # For example, with a test speed ratio of 5, the seconds to start for the
            # first race with an F flag start will be 600  / 5 = 120 seconds.
            #
            # For the five minute (300 seconds) gun, the calculation is:
            # 120 - (300/5) = 60 seconds.
            #
            # For the four minute gun (240 seconds) gun, the calculation is:
            # 120 - (240/5) = 72 seconds
            #
            secondsToGun = secondsToStart - secondsBefore / RaceManager.testSpeedRatio
            logging.info("Seconds to start: %d, scheduling gun for %d seconds" % (secondsToStart,secondsToGun))
            gunMillis = int(1000*secondsToGun )
            self.scheduleWarningBeeps(gunMillis)
            
            self.scheduleGun(gunMillis)
            
         
        
    
                            
    #
    # For a sequence start, we fire the gun then schedule our other guns. We ask the race manager to
    # adjust our start seconds to reflect if we have speedup the start for testing purposes.
    #
    def handleSequenceStartedWithWarning(self):
        # schedule ten second countdown
        self.scheduleWarningBeeps(10000)
        # schedule gun for ten seconds
        self.scheduleGun(10000)
        
        #
        # schedule beeps for F flag down in 4 minutes time
        #
        fFlagDownMillis = 10000 + (4 * 60000) / RaceManager.testSpeedRatio
        self.scheduleWarningBeeps(fFlagDownMillis, finalWarning=True)
        
        
        # schedule guns for the first fleet
        
        self.scheduleGunForFleetStart(self.raceManager.fleets[0],300)
        
        # schedule guns for future fleets
        
        self.scheduleGunsForFutureFleetStarts()
        
    def handleFinishAdded(self,aFinish):
        self.fireGun()
    
    def handleSequenceStartedWithoutWarning(self):
        # schedule ten second countdown
        self.scheduleWarningBeeps(10000)
        # schedule gun for ten seconds
        self.scheduleGun(10000)
        
        self.scheduleGunsForFutureFleetStarts()
    
    def handleGeneralRecall(self,aFleet):
        self.fireGun()
        self.fireGun()
        self.cancelSchedules()
        self.scheduleGunsForFutureFleetStarts()
        
    def handleStartSequenceReset(self):
        self.cancelSchedules()
    
    
    def scheduleGunsForFutureFleetStarts(self):
        #
        # iterate over all of the fleet. If the fleet is not started, schedule the guns
        #
        for aFleet in self.raceManager.fleets:
            if not aFleet.isStarted() :
                self.scheduleGunForFleetStart(aFleet,240)
                self.scheduleGunForFleetStart(aFleet,60)
                self.scheduleGunForFleetStart(aFleet,0)
                
       

def f1Pressed(event):
    print("F1 pressed")     
            
        
class ScreenController():
    pass

    def __init__(self,startLineFrame,raceManager,audioManager,easyDaqRelay,recoveryManager,defaultFleetNames,fontSize):
        self.startLineFrame = startLineFrame
        self.raceManager = raceManager
        self.audioManager = audioManager
        self.easyDaqRelay = easyDaqRelay
        self.recoveryManager = recoveryManager
        # needed to pass to add fleet dialog
        self.defaultFleetNames = defaultFleetNames
        # needed to pass to add fleet dialog
        self.fontSize = fontSize
        
        self.selectedFleet = None    
        self.selectedFinish = None
        
        self.fleetButtons=[]
        self.buildFleetManagerView()
        
        
        self.wireController()
        self.disableButtons()
        
        
   
    def disableButtons(self):
        self.startLineFrame.disableRemoveFleetButton()
        self.startLineFrame.disableResetStartRaceSequenceButton()
        
    

    def wireController(self):
        self.raceManager.changed.connect("fleetAdded",self.handleFleetAdded)
        self.raceManager.changed.connect("fleetRemoved",self.handleFleetRemoved)
        self.raceManager.changed.connect("fleetChanged",self.handleFleetChanged)
        self.raceManager.changed.connect("finishAdded",self.handleFinishAdded)
        self.raceManager.changed.connect("finishRemoved",self.handleFinishRemoved)
        self.raceManager.changed.connect("finishChanged",self.handleFinishChanged)
        self.raceManager.changed.connect("sequenceStartedWithWarning",self.handleSequenceStarted)
        self.raceManager.changed.connect("sequenceStartedWithoutWarning",self.handleSequenceStarted)
        
        #
        # Need to change this from event based to refreshing as part of the update loop
        #
        if self.easyDaqRelay:
            self.easyDaqRelay.changed.connect("connectionStateChanged",self.handleConnectionStateChanged)
        
        self.startLineFrame.addFleetButton.config(command=self.addFleetClicked)
        self.startLineFrame.removeFleetButton.config(command=self.removeFleetClicked)
        self.startLineFrame.fleetsTreeView.bind("<<TreeviewSelect>>",self.fleetSelectionChanged)
        self.startLineFrame.finishTreeView.bind("<<TreeviewSelect>>",self.finishSelectionChanged)
        self.startLineFrame.startRaceSequenceWithWarningButton.config(command=self.startRaceSequenceWithWarningClicked)
        self.startLineFrame.startRaceSequenceWithoutWarningButton.config(command=self.startRaceSequenceWithoutWarningClicked)
        self.startLineFrame.generalRecallButton.config(command=self.generalRecallClicked)
        self.startLineFrame.gunButton.config(command=self.gunClicked)
        self.startLineFrame.gunAndFinishButton.config(command=self.gunAndFinishClicked)
        self.startLineFrame.resetStartRaceSequenceButton.config(command=self.resetStartRaceSequenceClicked)
        self.startLineFrame.removeFinishButton.config(command=self.removeFinishClicked)
        self.startLineFrame.exitButton.config(command=self.exitClicked)
        self.startLineFrame.master.protocol("WM_DELETE_WINDOW",self.exitClicked)
        # bind F1 to gun and finish clicked. 
        # bind F2 to gun clicked
        # This is a useful keyboard shortcut and also provides support for additional HID
        # devices that are configured to keyboard events
        
        self.startLineFrame.bind_all("<F1>",self.f1Pressed)
        self.startLineFrame.bind_all("<F2>",self.f2Pressed)
        
        
        
    def buildFleetManagerView(self):
        # we build our tree
           
        for fleet in self.raceManager.fleets:
            self.appendFleetToTreeView(fleet)
    
    
    def appendFleetToTreeView(self,aFleet):
        self.startLineFrame.fleetsTreeView.insert(
             parent="",
             index="end",
             iid = aFleet.fleetId,
             text = aFleet.name,
             values=(self.renderDeltaToStartTime(aFleet),aFleet.status()))  
            
    def showAddFleetDialog(self):
        addFleetDialog = AddFleetDialog(self.startLineFrame,self.defaultFleetNames)
        # ... build the window ...
        
        ## Set the focus on dialog window (needed on Windows)
        addFleetDialog.top.focus_set()
        ## Make sure events only go to our dialog
        addFleetDialog.top.grab_set()
        ## Make sure dialog stays on top of its parent window (if needed)
        addFleetDialog.top.transient(self.startLineFrame)
        # set the position to be relative to the parent
        addFleetDialog.top.geometry("+%d+%d" % (self.startLineFrame.winfo_rootx()+50,
                                  self.startLineFrame.winfo_rooty()+50))
        ## Display the window and wait for it to close
        addFleetDialog.top.wait_window()
        return addFleetDialog.fleetName
    
    def addFleetClicked(self):
        fleetName = self.showAddFleetDialog()
        
        if fleetName:
            self.raceManager.createFleet(fleetName)
        self.updateButtonStates()
        
    def removeFleetClicked(self):#
        # check we have a selected fleet
        if self.selectedFleet:
            self.raceManager.removeFleet(self.selectedFleet)
        self.updateButtonStates()
            
    def startRaceSequenceWithWarningClicked(self):
        self.raceManager.startRaceSequenceWithWarning()
        self.updateButtonStates()
        
    
    def startRaceSequenceWithoutWarningClicked(self):
        self.raceManager.startRaceSequenceWithoutWarning()
        self.updateButtonStates()
        
        
    def generalRecallClicked(self):
        self.raceManager.generalRecall()
        self.updateButtonStates()
        
    def gunClicked(self):
        self.audioManager.queueClip("gun")


    def resetStartRaceSequenceClicked(self):
        result = tkMessageBox.askquestion("Reset race sequence","Are you sure? This will remove any finishes.", icon="warning")
        if result == 'yes':
            self.raceManager.resetStartSequence()
        self.updateButtonStates()
           
        
    def fleetSelectionChanged(self,event):
        item = self.startLineFrame.fleetsTreeView.selection()[0]
        
        self.selectedFleet = self.raceManager.fleetWithId(item)
        
        logging.debug("User has selected %s" % str(self.selectedFleet))
        self.updateButtonStates()
        
    def finishSelectionChanged(self,event):
        item = self.startLineFrame.finishTreeView.selection()[0]
        self.selectedFinish = self.raceManager.finishWithId(item)
        self.updateButtonStates()
        
    def f1Pressed(self,event):
        self.startLineFrame.gunAndFinishButton.invoke()
        
    def f2Pressed(self,event):
        self.startLineFrame.gunButton.invoke()
    
    def gunAndFinishClicked(self):
        logging.debug("Gun and finish clicked")
        self.raceManager.createFinish()
        
    def removeFinishClicked(self):
        self.raceManager.removeFinish(self.selectedFinish)
        self.selectedFinish = None
    
    def handleFleetAdded(self,aFleet):
        self.appendFleetToTreeView(aFleet)
        self.updateButtonStates()
        
    
    def handleFleetRemoved(self,aFleet):
        self.startLineFrame.fleetsTreeView.delete(aFleet.fleetId)
        self.selectedFleet=None
        self.updateButtonStates()
    
    
    def handleFleetChanged(self,aFleet):
        pass
    
    def handleFinishAdded(self,aFinish):
        self.appendFinishToFinishTreeView(aFinish)
        
    def handleFinishRemoved(self,aFinish):
        self.startLineFrame.finishTreeView.delete(aFinish.finishId)
        
    
    def handleFinishChanged(self,aFinish):
        # update the GUI for a finish
        self.startLineFrame.finishTreeView.item(aFinish.finishId,
            values=(self.renderFinishFleet(aFinish),self.renderFinishElapsedTime(aFinish)))
    
    def buildFinishView(self):
        # we build our tree
           
        for finish in self.raceManager.finishes:
            self.appendFinishToFinishTreeView(finish)
            
    #
    # When the sequence starts, we create our fleet buttons
    #
    def handleSequenceStarted(self):
        
        self.createFleetButtons()
        
    def createFleetButtons(self):
        
        for i in range(len(self.raceManager.fleets)):
            fleet = self.raceManager.fleets[i]
            buttonText = fleet.name.replace(" ","\n")
            fleetButton = self.startLineFrame.createFleetButton(buttonText,i)
            
            # we're creating multiple lambdas within the same namespace.
            # This workaround comes from http://stackoverflow.com/questions/4236182/generate-tkinter-buttons-dynamically
            
            fleetButton.configure(command=lambda fleet=fleet: self.handleFleetButtonClickedForFleet(fleet=fleet))
            self.fleetButtons.append(fleetButton)
            
            
    def enableFleetButtons(self):
        for button in self.fleetButtons:
            button['state'] = Tkinter.NORMAL
            
    def disableFleetButtons(self):
        for button in self.fleetButtons:
            button['state'] = Tkinter.DISABLED
        
    
    def handleFleetButtonClickedForFleet(self,fleet):
        logging.info("Fleet button " + fleet.name + " clicked")
        if self.selectedFinish:
            self.selectedFinish.fleet = fleet
            self.raceManager.updateFinish(self.selectedFinish)
            self.selectFinishInTreeView(self.nextFinishWithoutFleetAfter(self.selectedFinish))
    
    def nextFinishWithoutFleetAfter(self,finish):
        indexOfFinish = self.raceManager.finishes.index(finish)
        for i in range(indexOfFinish+1,len(self.raceManager.finishes)):
            if not self.raceManager.finishes[i].hasFleet():
                return self.raceManager.finishes[i]
            
        return None
    #
    def appendFinishToFinishTreeView(self,aFinish):
        finishItem = self.startLineFrame.finishTreeView.insert(
             parent="",
             index="end",
             iid = aFinish.finishId,
             text = self.renderFinishTime(aFinish),
             values=(self.renderFinishFleet(aFinish),self.renderFinishElapsedTime(aFinish)))
        
        # the call up update_idletasks is needed to make sure that the
        # treeview is fully populated. Without this line, on Active Python 2.7.2.5
        # the scroll to the bottom only works every other item. 
        self.startLineFrame.update_idletasks()
        self.startLineFrame.finishTreeView.see(finishItem)
        
        #
        # if we don't already have a selected finish, 
        # or select the fleet just added
        #
        if not self.selectedFinish or self.selectedFinish.hasFleet():
            self.selectFinishInTreeView(aFinish)
    
    
    #
    # This isn't quite right. 
    #
    
    def selectFinishInTreeView(self,aFinish):
        # if we do have a finish
        if aFinish:
            self.startLineFrame.finishTreeView.selection_set(aFinish.finishId)
            self.selectedFinish = aFinish
            self.enableFleetButtons()
        else:
        # if we don't have a finish
            selectedItems = self.startLineFrame.finishTreeView.selection()
            self.startLineFrame.finishTreeView.selection_set(selectedItems)
        self.updateButtonStates()
    
    #
    # Render the fleet of a finish
    #
    def renderFinishFleet(self,aFinish):
        # if our finish has a fleet, return the name of the fleet
        if aFinish.fleet:
            return aFinish.fleet.name
        else:
            return "-"
        
    #
    # Render the finish time. This is the clock time of the finish
    #
    def renderFinishTime(self,finish):
        return finish.finishTime.strftime("%H:%M:%S")
    
    def renderFinishElapsedTime(self,finish):
        # if we have a fleet, calculate the delta from the finish time to the 
        # start time of the fleet.
        if finish.hasFleet():
            
            
            
            return str(int(finish.elapsedFinishTimeDelta().total_seconds()))
        #
        # if we don't have a fleet, we can't calculate the elapsed time
        #
        else:
        
            return "-"
        
            
    #
    # event handler for the connection state of the easyDaqRelay changing
    #
    def handleConnectionStateChanged(self,state):
        # update the Tk string variable with the session state description
        # from the EasyDaq relay object
        self.startLineFrame.after(0, self.updateSessionStateDescription)
        
    def updateSessionStateDescription(self):
        if self.easyDaqRelay:
            while self.easyDaqRelay.sessionStateDescriptionQueue.qsize():
                try:
                    message = self.easyDaqRelay.sessionStateDescriptionQueue.get_nowait()
                    self.startLineFrame.connectionStatus.set(message)
                except Queue.Empty:
                    # this should never happen. 
                    message = "Lights: No message available"
                    
    
    #
    # Calculate the integer adjusted seconds to start time. This is counter-intuitive: the
    # effect of the int function is to subtract 1 second almost all of the time. If the
    # result is 1.99999 seconds, int will reduce to 1. So we add 1 second
    # to the float value. This reflects the behaviour
    # of a regular clock. On a countdown, we show the time as 2 seconds until it is
    # exactly 1 second.
    #
    def integerAdjustedDeltaSecondsToFleetStartTime(self,aFleet):
        return int(aFleet.adjustedDeltaSecondsToStartTime()-1)
    
    def renderDeltaToStartTime(self, aFleet):
        if aFleet.hasStartTime():
            deltaToStartTimeSeconds = int(self.integerAdjustedDeltaSecondsToFleetStartTime(aFleet))
            
            hmsString = str(datetime.timedelta(seconds=(abs(deltaToStartTimeSeconds))))
            
            if deltaToStartTimeSeconds < 0:
                return "-" +  hmsString 
            else:
                return hmsString
        
        else:
            return "-"
        
    
    
    def renderDeltaSecondsToStartTime(self, aFleet):
        if aFleet.hasStartTime():
            return self.integerAdjustedDeltaSecondsToFleetStartTime(aFleet)
            
            
            
        else:
            return "-"
        
    
    def refreshFleetsView(self):
        #
        # iterate over all of our fleets. Read the start time delta and
        # and status, and update the fleetsTreeView with their values
        #
        
        for aFleet in self.raceManager.fleets:
            
            self.startLineFrame.fleetsTreeView.item(
                        aFleet.fleetId,
                        
                        values=[self.renderDeltaToStartTime(aFleet), self.renderDeltaSecondsToStartTime(aFleet),aFleet.status()])
        
       
        
        #
        # Ask our race manager if we have a started fleet and last fleet started was started less than 30 seconds ago
        #
            
        if self.raceManager.hasStartedFleet() and self.raceManager.lastFleetStarted().adjustedDeltaSecondsToStartTime() < 30.0:
            self.startLineFrame.enableGeneralRecallButton()
        else:
            self.startLineFrame.disableGeneralRecallButton()
    
            
                  
        #
        # Update our clock
        #
        self.startLineFrame.clockStringVar.set(datetime.datetime.now().strftime("%H:%M:%S"))
        
        #
        # Update the connection status
        #
        self.updateSessionStateDescription()
        
        #
        # Update the wav file queue depth
        #
        self.updateGunQueueLength()
    
        #
        # Schedule to update this view again in 250 milliseonds
        #
        self.startLineFrame.after(250, self.refreshFleetsView)
    
    
    #
    # This method enables and disables buttons. Call it after handling a button event
    #
    def updateButtonStates(self):
        #
        # Logic for enabling and disabling buttons
        #   
        if self.raceManager.hasSequenceStarted() or self.raceManager.hasStartedFleet(): 
            
            self.startLineFrame.enableResetStartRaceSequenceButton()
            self.startLineFrame.disableAddFleetButton()
            self.startLineFrame.disableRemoveFleetButton()
            self.startLineFrame.disableStartRaceSequenceWithoutWarningButton()
            self.startLineFrame.disableStartRaceSequenceWithWarningButton()
           
        else:
            self.startLineFrame.enableAddFleetButton()
            self.startLineFrame.disableResetStartRaceSequenceButton()
            
            
            if self.raceManager.hasFleets():
            
            
                
                self.startLineFrame.enableStartRaceSequenceWithoutWarningButton()
                self.startLineFrame.enableStartRaceSequenceWithWarningButton()
                if self.selectedFleet:
                    self.startLineFrame.enableRemoveFleetButton()
                else:
                    self.startLineFrame.disableRemoveFleetButton()
            else:
                self.startLineFrame.disableRemoveFleetButton()
                self.startLineFrame.disableStartRaceSequenceWithoutWarningButton()
                self.startLineFrame.disableStartRaceSequenceWithWarningButton()
  
    
        if self.selectedFinish:
            self.enableFleetButtons()
        else:
            self.disableFleetButtons()
    #
    # start the controller. Every 500 milliseconds we refresh the start time and the status
    # of the race manager 
    #
    def start(self):
        # if we have recovered, we need to build our finish view and our fleet buttons
        self.buildFinishView()
        self.createFleetButtons()
        
        self.startLineFrame.after(500, self.refreshFleetsView)
        
    #
    # The gun queue has changed. Update the UI to show the length of the gun queue
    #
    def updateGunQueueLength(self):
        
        self.startLineFrame.gunQueueCount.set("Gun Q : %d " % self.audioManager.queueLength())


    def exitClicked(self):
        result = tkMessageBox.askquestion("Exit","Are you sure?", icon="warning")
        if result == 'yes':
            self.shutdown()
        
    def shutdown(self):
        
        logging.info("Shutting down")
        if self.easyDaqRelay:
            self.easyDaqRelay.sendRelayCommand([LIGHT_OFF, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF])
            self.easyDaqRelay.stop()
        
        # delete our recovery file if we have one
        if self.recoveryManager:
            self.recoveryManager.stop()
        
        # and then quit after a second
        self.startLineFrame.after(1000,self.startLineFrame.master.quit)

