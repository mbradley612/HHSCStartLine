'''
Created on 20 Jan 2014

The audio manager plays audio clips loaded from WAV files asynchronously. As per http://joyrex.spc.uchicago.edu/bookshelves/python/cookbook/pythoncook-CHP-9-SECT-7.html
Tk should be insulated from any external IO.

See http://people.csail.mit.edu/hubert/pyaudio/ for details of PyAudio

You will need to download PyAudio, see http://people.csail.mit.edu/hubert/pyaudio/#downloads

@author: MBradley
'''
import pyaudio
import wave
import Queue
import time
import logging

from StringIO import StringIO

CHUNK=1024

class AudioClip:
    def __init__(self, wavFilename):
        self.wavFilename = wavFilename
        self.readFileToMemory()
        self.wavDuration = self.calculateDuration()

    def readFileToMemory(self):
        # see http://stackoverflow.com/questions/8195544/how-to-play-wav-data-right-from-memory
        fileOnDisk = open(self.wavFilename,'rb')
        self.fileInMemory = StringIO(fileOnDisk.read())
        fileOnDisk.close()


    def calculateDuration(self):
        self.openWav()
        numberFrames = self.wav.getnframes()
        rate = self.wav.getframerate()
        duration = int(1000 * (numberFrames / float(rate)))
        return duration

    def openWav(self):
        self.fileInMemory.seek(0)
        self.wav = wave.open(self.fileInMemory)
        pass
                

    
    def playOn(self,audioManager):
        self.openWav()
        audioManager.playWav(self.wav)
        
        



class AudioManager:
    
    #
    # Parameter is a list of tuples of symbolic name of wav and filename, e.g
    # [('horn','c:\music\horn.wav),('beep','c:\music\beep.wav')]
    #
    def __init__(self, wavFiles):
        # create our instance of PyAudio
        self.portAudio = pyaudio.PyAudio()
        # create a dictionary of audio clips           
        self.audioClips = {}
        
        for (clipname,wavFilename) in wavFiles:
            
            self.audioClips[clipname] = AudioClip(wavFilename)
            

        self.commandQueue = Queue.Queue()
        self.isPlaying = False
        
        
    
    


    def playClip(self,clipName):
        self.isPlaying = True
        logging.debug("Playing wav")
        self.audioClips[clipName].playOn(self)

        
    def playWav(self,wav):
        stream = self.portAudio.open(format=self.portAudio.get_format_from_width(wav.getsampwidth()),
                channels=wav.getnchannels(),
                rate=wav.getframerate(),
                output=True)
        data = wav.readframes(CHUNK)
        while data != '':
            stream.write(data)
            data = wav.readframes(CHUNK)
        stream.stop_stream() 
        stream.close()
            
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
        self.portAudio.terminate()
            
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
        
        

