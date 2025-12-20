'''
Created on 29 Jul 2014

@author: MBradley
'''

#
# This module contains classes for persisting the StartLine racemanager to disk. It gets notified when the race manager changes and writes a pickled
# race manager (without its signal object) to the pickle file. 
#

#
# The race recovery manager uses the pickle module to dump the race manager to a string whenever the race changes. The manager writes to
# file in its own thread to minimise the risk of IO issues on the user interface TK event queue.
#

import os
import pickle
import logging
import queue

class RaceRecoveryManager:
    def __init__(self,pickleFilename,raceManager):
        self.pickleFilename = pickleFilename
        self.raceManager = raceManager
        self.saveQueue = queue.Queue() 
        
    def hasRecoveryFile(self):
        return os.path.exists(self.pickleFilename)
    
    
    def readPickledRaceManager(self):
        with open(self.pickleFilename,"rb") as pickleFile:
            pickledRaceManager = pickle.load(pickleFile)

        return pickledRaceManager
    
    def writeRecoveryFile(self,fileContents):
        #
        #
        with open(self.pickleFilename,"wb") as recoveryFile:
            recoveryFile.write(fileContents)
        
    def raceManagerChanged(self,aRaceManager):
        self.handleRaceManagerChanged()
        
    def handleRaceManagerChanged(self,*args):
        
        self.saveQueue.put(pickle.dumps(self.raceManager))
        
    #
    # This method gets called in its own thread
    #
    def run(self):

        self.isRunning = True
        while self.isRunning:
            try:
                logging.debug("Waiting on save queue")
                pickledRaceManager = self.saveQueue.get(block=True)
                self.writeRecoveryFile(pickledRaceManager)
                
            except queue.Empty:
                # we do nothing if the queue is empty. This should never happen, because we are
                # blocking for ever.
                pass
    
    #
    # when we are asked to stop, we delete the recovery file
    #
    def stop(self):
        
        self.isRunning = False
        
        if self.hasRecoveryFile():
            os.remove(self.pickleFilename)