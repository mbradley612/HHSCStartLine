'''
Created on 20 Jan 2014

12 March 2015 

Changed to use pygame's mixer because of performance issues with PyAudio/PortAudio on
Raspberry Pi. No change required to the interface to the AudioManager. 
See https://github.com/mbradley612/HHSCStartLine/issues/18 

There is now a dependency on PyGame. This is installed by default on a Raspberry Pi. On Windows,
you have to install the MSI installer for PyGame from http://www.pygame.org/download.shtml 


We use the pygame mixer in a blocking type pattern, following the recipe at:
http://code.activestate.com/recipes/521884-play-sound-files-with-pygame-in-a-cross-platform-m/

This means that we can avoid using the pygame event queue - this would require initializing
the pygame video module which we don't want to do.

@author: MBradley
'''
import pygame
import Queue
import logging


FREQ = 44100   # same as audio CD
BITSIZE = -16  # unsigned 16 bit
CHANNELS = 2   # 1 == mono, 2 == stereo
BUFFER = 1024  # audio buffer size in no. of samples
FRAMERATE = 30  # how often to check if playback has finished

class AudioClip:
    def __init__(self, wavFilename):
        
        self.sound = pygame.mixer.Sound(wavFilename)
        
    
    def play(self):
        
        self.sound.play()
        
    def duration(self):
        return self.sound.get_length()
        

class AudioManager:
    
    #
    # Parameter is a list of tuples of symbolic name of wav and filename, e.g
    # [('horn','c:\music\horn.wav),('beep','c:\music\beep.wav')]
    #
    def __init__(self, wavFiles):
        # Initialize the pygame mixer. We do not initialize the whole of
        # pygame as this means initializing the pygame video system
        # which we don't need
        pygame.mixer.init(FREQ, BITSIZE, CHANNELS, BUFFER)
        
        self.channel = pygame.mixer.find_channel()
        self.clock = pygame.time.Clock()
        
        
        # create a dictionary of audio clips           
        self.audioClips = {}
        
        for (clipname,wavFilename) in wavFiles:
            
            self.audioClips[clipname] = AudioClip(wavFilename)
            

        self.commandQueue = Queue.Queue()
        self.isPlaying = False
        
        
    
    


    def playClip(self,clipName):
        self.isPlaying = True
        logging.debug("Playing wav")
        self.audioClips[clipName].play()
        while pygame.mixer.get_busy():
            
            self.clock.tick(FRAMERATE)

               
    #
    # The audio manager is designed to run synchronously in its own thread, using a Queue.Queue
    # to queue requests to play audio files using a command pattern.    #
    def run(self):
        self.isRunning = True
        while self.isRunning:
            try:
                logging.debug("Waiting on audio manager command queue")
                command = self.commandQueue.get(block=True)
                command.executeOn(self)
                
            except Queue.Empty:
                # we do nothing if the queue is empty. This should never happen, because we are
                # blocking for ever.
                pass
        pygame.mixer.quit()
            
    #
    # This method is called from within the Tkinter event thread.
    #
    def queueClip(self,clipName):
        self.commandQueue.put(AudioManagerPlayClip(clipName))
        
    
    def stop(self):
        self.commandQueue.put(AudioManagerStop())
    
    #
    # if you want to know how many queued, check for the queue length
    #
    def queueLength(self):
        return self.commandQueue.qsize()
        

class AudioManagerCommand:
    def executeOn(self, anAudioManager):
        pass
    
class AudioManagerPlayClip(AudioManagerCommand):
    def __init__(self,clipName):
        self.clipName = clipName
        
    def executeOn(self, anAudioManager):
        anAudioManager.playClip(self.clipName)
        
class AudioManagerStop(AudioManagerCommand):
    def executeOn(self, anAudioManager):
        anAudioManager.isRunning = False
        
        

