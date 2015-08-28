'''
Created on 3 Jan 2015

This python module should be deployed in the "root" directory of a zip file. This
facilitates "running" the zip file, e.g. python startline.zip. 

@author: MBradley
'''
from screenui.raceview import StartLineFrame,AddFleetDialog
from model.race import RaceManager
from screenui.audio import AudioManager
from persistence.recovery import RaceRecoveryManager

import threading 
import logging
import logging.config
import sys
import ConfigParser
import os
import tkMessageBox
import pickle
from controllers.controllers import ScreenController, GunController,\
    LightsController
from logging.handlers import TimedRotatingFileHandler

#
# to manage our sub-process, we must ensure that our main is only invoked once, here. Otherewise
# the subprocess will also invoke this code.
#
#----------------------------------------------------------------------
def create_timed_rotating_log(path):
    """"""
    logger = logging.getLogger("Rotating Log")
    logger.setLevel(logging.INFO)
 
    handler = TimedRotatingFileHandler(path,
                                       when="m",
                                       interval=1,
                                       backupCount=5)
    logger.addHandler(handler)

if __name__ == '__main__':
    
    if not len(sys.argv) == 2:
        sys.stderr.write("Usage: pass ini filename as parameter")
        exit(1) 
    configFilename = sys.argv[1]   
    
    sys.stderr.write("Reading config from %s\n" % configFilename)     
    if not os.path.isfile(configFilename):
        sys.stderr.write("Config file not found")
        exit(1)
    
    config = ConfigParser.ConfigParser()

    config.read(configFilename)
    
    
    logConfigFilename = config.get("Logging","configFilename")
    sys.stderr.write("Reading log file config from %s\n" % logConfigFilename)
    
    logging.config.fileConfig(logConfigFilename)            
    
    if config.get("Lights","enabled") == 'Y':
        lightsEnabled = True
        comPort = config.get("Lights","comPort")
        logging.info("Lights enabled on COM port %s" % comPort)
    else:
        lightsEnabled = False
        logging.info("Lights not enabled")
        
    
    if config.get("Training","trainingMode") =='Y':
        testSpeedRatio = config.getint("Training","trainingSpeed")
        logging.info("Running in training mode at speed %i" % testSpeedRatio)
    else:
        testSpeedRatio = 1
        logging.info("Running in race mode at standard speed")
        
    
    #
    # config.items returns a list of (name,value) pairs.
    # In the Audio section, this is clipname,wavFilename
    #
    
    audioClips = config.items("Audio")
    
    
    
    backgroundColour = config.get("UserInterface","backgroundColour")        
    if config.get("UserInterface","fullScreen") == 'Y':
        fullScreen = True
    else:
        fullScreen = False
    if config.get("UserInterface","fontSize"):
        fontSize = int(config.get("UserInterface","fontSize"))
    else:
        fontSize = 10
    app = StartLineFrame(backgroundColour=backgroundColour,fullScreen=fullScreen,fontSize=fontSize)
    
      
    #
    # Check for a recovery file. If we have one, ask if we want to recover our race manager
    #
    recoveryFilename = config.get("Persistence","recoveryFilename") 
    if recoveryFilename:
        if os.path.exists(config.get("Persistence","recoveryFilename")):
            if tkMessageBox.askyesno("Crash detected","Do you want to recover?", icon="warning"):
                raceManager = pickle.load(open(recoveryFilename))
            else:
                raceManager = RaceManager()
        else:
            raceManager = RaceManager()
    else:
        raceManager = RaceManager()
    
    if testSpeedRatio:
        RaceManager.testSpeedRatio = testSpeedRatio
    logging.info("Setting test speed ratio to %d" % testSpeedRatio)
    easyDaqRelay = None
    
    if lightsEnabled:     
        from lightsui.hardware import LIGHT_OFF, LIGHT_ON, EasyDaqUSBRelay
        
        easyDaqRelay = EasyDaqUSBRelay(comPort)
        relayThread = threading.Thread(target = easyDaqRelay.run)
        # run as a background thread. Allow application to end even if this thread is still running.
        relayThread.daemon = True
        
    # the audio manager runs in its own thread    
    audioManager = AudioManager(audioClips)  
    audioThread = threading.Thread(target = audioManager.run)
    audioThread.daemon = True
    
    
    recoveryManager = None
    if config.get("Persistence","recoveryFilename"):
        recoveryManager = RaceRecoveryManager(config.get("Persistence","recoveryFilename"),raceManager)
        raceManager.changed.connect(None,recoveryManager.handleRaceManagerChanged)
        recoveryThread = threading.Thread(target = recoveryManager.run)
        recoveryThread.daemon = True
        recoveryThread.start()
    if config.get("UserInterface","defaultfleetNames"):
        # the names of the fleets are split by "," in the config file
        defaultFleetNames = config.get("UserInterface","defaultfleetNames").split(",")
    else:
        defaultFleetNames= []
    
    screenController = ScreenController(app,raceManager,audioManager,easyDaqRelay, recoveryManager,defaultFleetNames,fontSize)
    gunController = GunController(app, audioManager, raceManager)
    # check if a recovered raceManager has a started sequence. If so, schedule guns.
    # note, this does not recover the F flag up beeps and gun nor F flag down beeps
    if raceManager.hasSequenceStarted():
        gunController.scheduleGunsForFutureFleetStarts()
    
    
    logging.info("Starting screen controller")             
    screenController.start()
    
    if lightsEnabled:
        lightsController = LightsController(app, easyDaqRelay, raceManager)
        logging.info("Starting lights controller") 
        relayThread.start()
    audioThread.start()
    app.master.title('Startline')    
    app.mainloop()  