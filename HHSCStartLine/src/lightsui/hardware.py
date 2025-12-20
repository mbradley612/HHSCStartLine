'''
Created on 26 Jan 2014

@author: MBradley
'''
import logging
import queue
import datetime
import time

import serial
from model.utils import Signal

# constants for lights state
LIGHT_OFF = 0
LIGHT_ON = 1

# constants for serial port session state
DISCONNECTED = 0
RECONNECTING = 1
CONNECTED = 2


'''
EasyDayUSBRelay wraps an EasyDaq USB relay board. It has its own python thread for
managing itself.

17/04/2014 - issue 2 - changed EasyDaqUSBRelay to run in its own thread to isolate the IO
from the rest of the application. This means that the relay changes from an asynchronous model running on the Tk event loop to 
a synchronous model. The performance overhead is not an issue for this application. The interface to the relay becomes
a queue of command objects to change the state of the relay.  
'''
class EasyDaqUSBRelay:

    def __init__(self, serialPortName):
        # capture the name of the serial port. On windows, this will be COM3, COM4 etc. The COM port is set
        # when the relay card is first plugged into the PC. You can change it subsequently through the control panel.
        self.serialPortName = serialPortName
        
        #
        # we use a python queue as our command interface, both internally and externally
        #
        self.commandQueue = queue.Queue()
        
        #
        # we use a python queue as our session state description output mechanism. This insulates the GUI from the threading
        # of the relay
        #
        self.sessionStateDescriptionQueue = queue.Queue()
        
        #
        # we use a signal pattern to notify events
        #
        self.changed = Signal()
        
        #
        # we create our serial port connection now. We don't open the connection until we are asked to connect
        #
        # timeout is set to 0.5 second for reads. 
        self.serialConnection = serial.Serial(timeout=0.5)
        
        # and tell the serial connection which serial port to connect
        self.serialConnection.port = self.serialPortName      
        
        # the baud rate is always 9600
        self.serialConnection.baudrate = 9600
        
        #
        # track whether or not we are enabled. If we are enabled, then we continue to check that have an active connection
        # and if not, we try to open the serial port. We start with not being enabled. As soon as we asked to connect,
        # we are enabled.
        #
        self.isEnabled = False
        
                
        #
        # track the time of the last command. We default to now as the startup time
        #
        self.lastPacketTime = datetime.datetime.now()
        
        #
        # trace the previous relay command. This enables us to resend in the event of a disconnect
        #
        self.currentRelayCommand = None
        self.previousRelayCommand = None
        
        #
        # We track our session status through constants DISCONNECTED,RECONNECTING,CONNECTED
        #
        self.sessionState = DISCONNECTED
            
    def setSessionState(self,state):
        self.sessionState = state
        logging.info("Session state is %s" % self.sessionStateDescription())
        self.sessionStateDescriptionQueue.put(self.sessionStateDescription())
        
        
    def beConnected(self):
        self.setSessionState(CONNECTED)
        
    def beNotConnected(self):
        self.setSessionState(DISCONNECTED)
        
    def beReconnecting(self):
        self.setSessionState(RECONNECTING)
        
        
    def sessionStateDescription(self):
        if self.sessionState == CONNECTED:
            return "CONNECTED"
        elif self.sessionState == DISCONNECTED:
            return "Warning: DISCONNECTED"
        elif self.sessionState == RECONNECTING:
            return "Warning: DISCONNECTED ATTEMPTING TO RECONNECT"
        
    def isConnected(self):
        return self.sessionState == CONNECTED
        
    def isDisconnected(self):
        return self.sessionState == DISCONNECTED
        
    def isReconnecting(self):
        return self.sessionState == RECONNECTING
            
    def processedCommand(self):
        '''
        We've processed a command. Capture the current date time.
        '''
        self.lastCommandProcessedTime = datetime.datetime.now()
        
    def maintainSession(self):
     
        if self.isConnected():
            logging.debug("Maintaining session")
            
            
            try:
                
                # create a relay packet that requests the EasyDaq to output its status
                self.currentRelayPacket = 'A' + chr(0)
                # and queue a request
                self.queuePacketToEasyDaq()
                
                # sleep for half a second
                time.sleep(0.5)
                # and read
                self.readSession()
                
            except (serial.SerialException):
                logging.exception("Exception writing read request to session")
                self.beNotConnected()
                self.reconnect()
        
    
    def readSession(self):
        logging.debug("Reading from session")
        try:
            # read a single byte. This should be our current status but at the moment we don't check for that
            x = self.serialConnection.read()
            logging.debug("Read from session")
            
        except (serial.SerialException, ValueError) as e:
            logging.error("I/O error: {0}".format(e))
            self.serialConnection.close()
            self.beReconnecting()
            self.reconnect()
    
    
    def establishSession(self):
        logging.debug("Establishing session in state: %s" % self.sessionStateDescription() )
        self.sendRelayConfiguration([0,0,0,0,0])
        
        previousState = self.sessionState
        
        # and be connected
        self.beConnected()
        
        if previousState == RECONNECTING:
                
            if self.currentRelayCommand:
                logging.info("Recovering ... sending current relay command: %s" % self.printableCommand(self.currentRelayCommand))
                self.currentRelayPacket = self.currentRelayCommand
                self.queuePacketToEasyDaq()
            elif self.previousRelayCommand:
                logging.info("Recovering ... sending previous relay command: %s" % self.printableCommand(self.previousRelayCommand))
                self.currentRelayPacket = self.previousRelayCommand
                self.queuePacketToEasyDaq()
        
    
    def _connect(self):
        # we are sometimes trying to connect when we are already
        # connected
        if not self.isConnected():
            logging.debug("Connecting to serial port")
            self.enabled = True
            try:
                # try to open the serial port
                if self.serialConnection.isOpen():
                    logging.debug("Request to open serial port when already open")
                else:
                    self.serialConnection.open()
                    logging.debug("Connected to serial port")
                # wait for a second and establish the session
                time.sleep(2)
                self.establishSession()
            
            except (serial.SerialException,ValueError) as e:           
                logging.error("I/O error: {0}".format(e))
                self.serialConnection.close()
                self.beReconnecting()
                self.reconnect()
        else:
            logging.debug("Request for connect when already connected")
            
    
    def reconnect(self):
        logging.info("Reconnecting to serial port")
        # sleep for 5 seconds
        time.sleep(5)
        # connect
        self._connect()
        
        
    def connect(self):
        self.commandQueue.put(EasyDaqUSBConnect())
        

    
    def disconnect(self):
        self.enabled = False
        if self.isConnected:
            self.serialConnection.close()
            self.beNotConnected()
        
    def timeSinceLastPacket(self):
        '''
        calculate the time since the last command
        '''
        deltaSinceLastPacket = datetime.datetime.now() - self.lastPacketTime
        
        return int((deltaSinceLastPacket.microseconds/1000) + deltaSinceLastPacket.seconds*1000)
    
    
    def writePacketToEasyDaq(self):
        # if we are connected, we write our packet
        try:
            logging.debug("Writing to serial port: %s" % self.printableCommand(self.currentRelayPacket))
            self.serialConnection.write(self.currentRelayPacket)
            
            #
            # Not the most elegant, but we check to see if this packet is a command by looking for a C as the first byte of the packet
            #
            if self.currentRelayPacket[0] =='C':
                
                self.previousRelayCommand = self.currentRelayCommand
                self.currentRelayCommand = None

            
            self.lastPacketTime = datetime.datetime.now()
        except (serial.SerialException,ValueError) as e:
            logging.error("I/O error: {0}".format(e))
            self.serialConnection.close()
            self.beReconnecting()
            
            self.reconnect()
    
    def printableCommand(self,relayCommand):
        return relayCommand[0] + "," + str(ord(relayCommand[1]))
    
    def queuePacketToEasyDaq(self):
        '''
        Write a command to EasyDaq. If we have written a command within the last 100 milliseconds,
        then delay by 100 milliseconds, otherwise write the command now.
        '''
        # easy scenario is that we can write the command immediately
        
        
        # if time delta is at least 100 milliseconds
        
        if (self.timeSinceLastPacket() > 100):
            # we can write the command now.
            self.writePacketToEasyDaq()
                
        else:
            # and queue to be written in 100 milliseconds
            logging.debug("Queuing writing packet to easyDaq")
            time.sleep((100-self.timeSinceLastPacket())/1000)
            self.writePacketToEasyDaq()


    #
    # This forms part of the external interface that will be invoked in a different thread.
    # Encapsulate in an object and put on a queue for execution.
    #
    def sendRelayConfiguration(self,relayArray):
        
        
        self.commandQueue.put(EasyDaqUSBSendRelayConfiguration(relayArray))
     

    #
    # This forms part of the external interface that will be invoked in a different thread.
    # Encapsulate in an object and put on a queue for execution.
    #
    def sendRelayCommand(self,relayArray):
     
        
        self.commandQueue.put(EasyDaqUSBSendRelayCommand(relayArray))
    
    def _sendRelayCommand(self,relayArray):
        # turn the values in the list into a byte where the bit in the byte reflects the position in the list.
        
        commandValue = 0
        
        for i in range(len(relayArray)):
                bitValue = (relayArray[i] *  pow(2,i))
                commandValue = commandValue + bitValue
        
        logging.debug("Sending C + %i" % commandValue)
        relayCommand = 'C' + chr(commandValue)
        self.currentRelayCommand = relayCommand
        
        self.currentRelayPacket = relayCommand
        # if we are connected, we queue the packet. If we are not connected,
        # the session recovery will play in the relay packet
        if self.isConnected():
            self.queuePacketToEasyDaq()

       
    def _sendRelayConfiguration(self,relayArray):
        # turn the values in the list into a byte where the bit in the byte reflects the position in the list.
        
        commandValue = 0
        
        for i in range(len(relayArray)):
                bitValue = (relayArray[i] *  pow(2,i))
                commandValue = commandValue + bitValue
        
        logging.debug("Sending B + %i" % commandValue)        
        self.currentRelayPacket = 'B' + chr(commandValue)
        
        self.queuePacketToEasyDaq()
        
    
    #
    # run is effectively the main method for the EasyDaqRelay
    #
    def run(self):
        self.isRunning = True
        self._connect()
        while self.isRunning:
            
            # get the next command from the command queue. If we don't get a command after five seconds
            # maintain our session
            try:
                logging.debug("Waiting for next command on command queue.")
                nextCommand = self.commandQueue.get(timeout=5)
                logging.debug("Return from command queue")
                nextCommand.executeOn(self)
            except queue.Empty:
                logging.debug("Timeout on command queue. Maintaining session.")
                self.maintainSession()
        self.disconnect()
    
    def stop(self):
        self.commandQueue.put(EasyDaqUSBStop())
     
                
#
# We use the command pattern to provide the communication between external threads and the
# thread that runs the EasyDaqRelay
#            
class EasyDaqUSBCommand:
    
    #
    # command has one abstract method - execute method taking an
    # EasyDaqUSBRelay as a parameter
    #
    def executeOn(self,aRelay):
        pass
    
class EasyDaqUSBConnect(EasyDaqUSBCommand):
    def executeOn(self,aRelay):
        aRelay._connect()

class EasyDaqUSBStop(EasyDaqUSBCommand):
    def executeOn(self,aRelay):
        aRelay.isRunning = False        

class EasyDaqUSBSendRelayCommand(EasyDaqUSBCommand):
    def __init__(self,relayArray):
        self.relayArray = relayArray
    
    def executeOn(self,aRelay):
        aRelay._sendRelayCommand(self.relayArray)
        
        
class EasyDaqUSBSendRelayConfiguration(EasyDaqUSBCommand):
    def __init__(self,relayArray):
        self.relayArray = relayArray
    
    def executeOn(self,aRelay):
        aRelay._sendRelayConfiguration(self.relayArray)
                