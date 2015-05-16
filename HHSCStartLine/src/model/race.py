#
# racing.model
#


#
# This module contains the classes for running races to the requirements of
# Hill Head Sailing Club, Fareham, Hampshire www.hillheadsc.org.uk
#

#
# The over-riding design principle of the model is KISS (Keep It Simple, Stupid).
#
# To this end, despite the real time nature of running a race, the state of the
# objects in the model do not change in real time. A race has a startTime. This
# is a clock time, e.g. 1115. The countdown to or elapsed time from are calculated
# from the clock time. Races are managed by a RaceManager, which is similarly
# static.
#
# The model uses wx.lib.pubsub for the model to send events to listeners. The
# UIs can subscribe to
# events on Races and also the RaceManager. See
# http://wxpython.org/docs/api/wx.lib.pubsub-module.html
#
#

from datetime import datetime,timedelta
from utils import Signal
import logging


# As per ISAF rules, start minutes is 5
# START_SECONDS = 300
# WARNING_SECONDS=300
# But we can reduce this for testing
START_SECONDS=300
WARNING_SECONDS=300
LAST_START_GENERAL_RECALL_DELAY=60

class RaceException(Exception):
    def __init__(self, fleet, message):
        self.fleet = fleet
        self.message = message
    def __str__(self):
        return repr(self.fleet)+ self.message



class Boat:
    
    def __init__(self,sailNumber,boatClass,py=None):
        self.sailNumber = sailNumber
        self.boatClass = boatClass
        self.py= py
        self.finish = None
        
    def calculatePyAdjustedSeconds(self):
        return self.finish.elapsedFinishTimeDelta().total_seconds() * 1000 / self.py

#
# A fleet represents a fleet of boats in a race. You should not change
# the state of a race (its name or start time); do this through
# the race manager.
#
class Fleet:
    
    
    def __init__(self, name=None, startTime=None,fleetId=None):
        
        self.fleetId = str(fleetId)
        if name is None:
            name = "Fleet " + str(self.fleetId)
      
        self.name = name
        self.startTime = startTime
        self.boats = []
        

    #
    # Does this fleet have a start time?
    #
    def hasStartTime(self):
        return self.startTime != None

    #
    # Is this fleet running? This is synonymous with the fleet having
    # a start time
    #
    def isRunning(self):
        return self.hasStartTime()

    #
    # Has this fleet started? This means, did the fleet start in the past?
    #
    def isStarted(self):
        if self.hasStartTime():
            return datetime.now() > self.startTime
            
        else:
            return False


    def adjustedDeltaSecondsToStartTime(self):
        return self._deltaToStartTime().total_seconds() * RaceManager.testSpeedRatio
        
    #
    # This is the real seconds to start time.
    # 
    def deltaSecondsToStartTime(self):
        return self._deltaToStartTime().total_seconds()

    #
    # What's the delta to the start time of this fleet - negative
    # for yet to start, positive for already started. if no start time,
    # raises a RaceException.
    #
    def _deltaToStartTime(self):
        if self.hasStartTime():
            return datetime.now() - self.startTime
        else:
            raise RaceException(self, "Fleet has no start time")

    # we are starting if our start time is in 5 mins or less
    def isStarting(self):
        # we can only be starting if we have a start time
        if self.hasStartTime():
            if (START_SECONDS * -1) <= self.adjustedDeltaSecondsToStartTime() < 0:
                return True
            else:
                return False
        else:
            return False
        
    def isWaitingToStart(self):
        return self.hasStartTime() and not self.isStarted()

    #
    # Provide a string representation of the status of the fleet
    #
    def status(self):
        if not self.hasStartTime():
            # note sure about this description - ask Luke
            return "Pending"
        if self.isStarting():
            return "Starting"
        if self.isStarted():
            return "Started"
        if not self.isStarted():
            return "Waiting to start"
            

    def __str__(self):
        return self.name + " status: " + self.status()


#
# Finish represents a finish of a competitor in a race. The finish is decoupled from the
# competitor/boat, to enable the race officer to create many finishes and associate them
# with competitors later. It also supports a use case where there are finishes that
# are never associated with a competitor, typically because the race officer creates
# a finish in error. 
#
class Finish:
    
    
    
    def __init__(self,finishTime=None,fleet=None,finishId=None):
        self.fleet = fleet
        self.finishTime = finishTime
        # we store the finishid as a string because this is the way Tk references it
        self.finishId = str(finishId)
        
        
        
    def hasFleet(self):
        if self.fleet:
            return True
        else:
            return False
    
    def elapsedFinishTime(self):
        if self.hasFleet():
            return self.fleet.startTime + self.elapsedFinishTimeDelta()
        else:
            raise  RaceException("Cannot calculate elapsed time if no fleet")
    
    def elapsedFinishTimeDelta(self):
        if self.hasFleet():
            return self.finishTime - self.fleet.startTime
        else:
            raise RaceException("Cannot calculate elapsed time if no fleet")
    
        
#
# The race manager manages fleets and competitors, including creating new fleets,
# setting the start time for a fleet, running a race and performing
# a general recall.
#
# The race manager has a list of fleets. These are always sorted in
# the order that they will start.
#
class RaceManager:
    
    testSpeedRatio = 1
    
    def __init__(self):
        self.fleets = []
        self.fleetsById = {}
        self.changed = Signal()
        self.finishes = []
        self.finishesById = {}
        # we store these on the race manager so that they get pickled
        self.nextFleetId = 1
        self.nextFinishId = 1
        
    #
    # this method controls how the RaceManager is pickled. We want to avoid pickling the Signal object
    # stored on the changed attribute
    #
    def __getstate__(self):
        attributes = self.__dict__.copy()
        del attributes["changed"]
        
        return attributes
    
    #
    # this method controls how the RaceManager is unpickled. We need to set the changed attribute
    # as it is not part of the pickle
    #
    def __setstate__(self,d):
        self.__dict__ = d
        self.changed = Signal()
         

    def incrementNextFleetId(self):
        self.nextFleetId = self.nextFleetId + 1

    def incrementNextFinishId(self):
        self.nextFinishId = self.nextFinishId + 1


        

    def adjustedSeconds(self,unadjustedSeconds):
        return unadjustedSeconds * RaceManager.testSpeedRatio
    
    def unadjustedSecond(self,adjustedSeconds):
        return adjustedSeconds / RaceManager.testSpeedRatio
    
    #
    # Create a fleet, add to our fleets and return the fleet. If the name is not specified,
    # we create a name as 'Fleet N' where N is the number of fleets.
    #
    def createFleet(self, name=None):
        aFleet = Fleet(name=name,fleetId=self.nextFleetId)
        self.incrementNextFleetId()
        self.addFleet(aFleet)
        return aFleet
    
    def fleetWithId(self,fleetId):
        if fleetId in self.fleetsById:
            return self.fleetsById[fleetId]
        

    def addFleet(self, aFleet):
        self.fleets.append(aFleet)
        self.fleetsById[aFleet.fleetId] = aFleet
        self.changed.fire("fleetAdded",aFleet)
        

    def removeFleet(self, aFleet):
        if aFleet in self.fleets:
            positionInList = self.fleets.index(aFleet)
            self.fleets.remove(aFleet)
            del self.fleetsById[aFleet.fleetId]
            self.changed.fire("fleetRemoved",aFleet)
            
        else:
            raise RaceException("Fleet not found",aFleet)
            

    def numberFleets(self):
        return len(self.fleets)
    
    def hasFleets(self):
        return self.numberFleets() > 0

    #
    # Start our race sequence in ten seconds with a five minute warning before the first
    # fleet, i.e. 10 minutes to the first fleet start. This is F flag start
    #
    def startRaceSequenceWithWarning(self):
        logging.info("Start sequence with warning (F flag start)")
        fleetNumber = 0
        
        now = datetime.now()
        sequenceStart = now + timedelta(seconds=10)
        for fleet in self.fleets:
            fleetNumber = fleetNumber + 1
            
            startTime = sequenceStart + timedelta(
                seconds = (WARNING_SECONDS/RaceManager.testSpeedRatio + 
                        (START_SECONDS * fleetNumber)/RaceManager.testSpeedRatio))

            self.updateFleetStartTime(fleet,startTime)
        self.changed.fire("sequenceStartedWithWarning")


    #
    # Start our race sequence without a warning (i.e. class start)
    #
    def startRaceSequenceWithoutWarning(self):
        logging.info("Start sequence without warning (class flag start)")
        fleetNumber = 0
        now = datetime.now()
        
        sequenceStart = now + timedelta(seconds=10)
        
        for fleet in self.fleets:
            fleetNumber = fleetNumber + 1
            
            startTime = sequenceStart + timedelta(
                seconds = (START_SECONDS * fleetNumber)/RaceManager.testSpeedRatio)

            self.updateFleetStartTime(fleet,startTime)
        self.changed.fire("sequenceStartedWithoutWarning")
    #
    # Update the startTime for a fleet. Do this through the race manager
    # so that the race manager can signal the event change
    #
    def updateFleetStartTime(self, aFleet, startTime):
        aFleet.startTime = startTime
        # signal that the fleet start time has changed
        self.changed.fire("fleetChanged",aFleet)
        
            

    #
    # Find the last fleet started. This is a reverse search
    # of the fleets list for a started fleet.
    # Returns None if not found
    #
    def lastFleetStarted(self):
        for fleet in reversed(self.fleets):
            if fleet.isStarted():
                return fleet
        return None
    
    #
    # Fine the next fleet to start. If we don't have a fleet starting,
    # return None.
    #
    def nextFleetToStart(self):
        for fleet in self.fleets:
            if fleet.isStarting() or fleet.isWaitingToStart():
                return fleet
        return None


    def hasStartedFleet(self):
        return not self.lastFleetStarted() is None
    
    
    def hasSequenceStarted(self):
        if self.nextFleetToStart():
            return True
        else:
            return False
    
    
    #
    # Reset start sequence - set all fleets to no start time, and fire a signal
    #
    def resetStartSequence(self):
        for fleet in self.fleets:
            fleet.startTime = None
        self.removeAllFinishes()
        self.changed.fire("startSequenceReset")

    def lastFleet(self):
        return self.fleets[-1]

    #
    # Perform a general recall. This is always for the fleet that
    # has most recently started
    #
    def generalRecall(self):
        logging.info("General recall")
        fleetToRecall = self.lastFleetStarted()
        
        
        

        # if this is the last (or only) fleet, set its start time to be six
        # minutes from now
        if fleetToRecall == self.fleets[-1]:
            logging.info("General recall last fleet")
            self.updateFleetStartTime(fleetToRecall,datetime.now()
                                 + timedelta(seconds=(START_SECONDS+LAST_START_GENERAL_RECALL_DELAY)/RaceManager.testSpeedRatio))

        # otherwise kick the fleet to be the back of the queue,
        # with a start time five minutes after the last fleet
        else:
            
            self.removeFleet(fleetToRecall)
            lastFleet = self.fleets[-1]
            self.updateFleetStartTime(fleetToRecall,
                    lastFleet.startTime + timedelta(seconds=START_SECONDS/RaceManager.testSpeedRatio))
            self.addFleet(fleetToRecall)
            logging.log(logging.INFO, "General recall not last fleet. Moving to back of queue. Delta to start time now %d seconds",
                        fleetToRecall.adjustedDeltaSecondsToStartTime())
            
        self.changed.fire("generalRecall", fleetToRecall)

        
    #
    # Create a finish and add it to the race manager's list of finishes. 
    # This method returns a finish object. By default, the finish object will
    # have a finish time of now and no fleet.
    #
    def createFinish(self, fleet=None, finishTime=None):
        
        # if no finish time is supplied, set the finish time to be now
        if not finishTime:
            finishTime = datetime.now()
        # create the finish object
        
        # if we only have one fleet, this will be the fleet for the finish
        if self.numberFleets() == 1:
            fleet = self.fleets[0]
        
        aFinish = Finish(fleet=fleet,finishTime=finishTime,finishId=self.nextFinishId)
        self.incrementNextFinishId()
        
        self.addFinish(aFinish)
        
        return aFinish
        
    
    def addFinish(self,finish):
        # add it to our list of finish objects
        self.finishes.append(finish)
        self.finishesById[finish.finishId] = finish
        # fire a change signal
        self.changed.fire("finishAdded",finish)
        
    def removeFinish(self,finish):
        self.finishes.remove(finish)
        del self.finishesById[finish.finishId]
        self.changed.fire("finishRemoved",finish)
        
    def updateFinish(self,finish):
        self.changed.fire("finishChanged",finish)
        
    def removeAllFinishes(self):
        for finish in list(self.finishes):
            self.removeFinish(finish)
        
    def finishWithId(self,finishId):
        if finishId in self.finishesById:
            return self.finishesById[finishId]

    