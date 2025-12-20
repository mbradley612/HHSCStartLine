# Delcom Product USB HID G2 Python 2 Example
# Rev 0.1 Oct 6, 2016 - Intail release
# Tested on Python 2, Linux 4.4.11 v7+ and Raspbian 8.0 (jessie)

# Required Libraries
# PYUSB - To install use: sudo pip install pyusb

# This code defines the DelcomUSBDevice class and if run as main will run the examplecode()
# When using with your code import this file and examplecode() will not run.

#-----------------------------------------------------------------------------------#
# For a quick example copy the code below in to a python file and run it
# Make sure the DelcomPython.py is in the same directory
"""
from DelcomPython import DelcomUSBDevice

myDevice = DelcomUSBDevice()            # Start the class and find the device
if myDevice.find() == 0 :               # Test for find
    print "Failed to find the device. Program terminated."
    sys.exit(0)
    
myDevice.open()                                     # Open the device
print "Port0= ", myDevice.ReadPort0()               # Read port 0 value
myDevice.LEDControl(myDevice.LED3, myDevice.LEDON)  # Turn LED3 ON    
myDevice.close()                                    # Close the device

"""
#-----------------------------------------------------------------------------------#


#-----------------------------------------------------------------------------------#
# USB Access Rights
# By default all USB devices only have root rights. So you may need
# to either run the python script with sudo rights (sudo python name.py)
# or change the rights on the usb device. You can use chmod to change the
# rights temporally or you can use the the following to make it permanment.
# Edit this file-> $ sudo nano /etc/udev/rules.d/50-myusb.rules 
# Add this line -> SUBSYSTEMS=="usb", ATTRS{idVendor}=="0fC5", ATTRS{idProducts}=="b080", GROUP="users", MODE="0666"
# Save the file and reboot for changes to be effective. The above will make all USB devices with a vendor
# number of 0F5C and product number of B080 have all rights.
#-----------------------------------------------------------------------------------#


import sys
import struct
import time
import usb.core
import usb.util


#--------------------------------------------------------------------#
#------------------- CLASS: DelcomUSBDevice -------------------------#
#--------------------------------------------------------------------#
class DelcomUSBDevice(object):
    VENDOR_ID       = 0x0FC5    #: Delcom Product ID
    PRODUCT_ID      = 0xB080    #: Delcom Product ID
    INTERFACE_ID    = 0         #: The interface we use
    TIMEOUT         = 100       #: 100ms timeout
    LED1,LED2,LED3,LED4,LEDALL=1,2,4,8,0xF
    LEDOFF,LEDON,LEDBLINK = 0,1,2
    

    def find(self):
        self.deviceDescriptor = DeviceDescriptor(self.VENDOR_ID,
                                                 self.PRODUCT_ID,
                                                 self.INTERFACE_ID)
        self.device = self.deviceDescriptor.getDevice()
        if self.device:
            #print ('Found Delcom Device')
            self.conf = self.device.configurations[0]
            self.intf = self.conf.interfaces[0][0]
            return(1)
        else:
            #print >> sys.stderr, "Delcom Device Not Found!"
             return(0)


    def open(self):
        try:
            self.handle = self.device.open()
            self.handle.detachKernelDriver(0)
        except usb.USBError, err:
            if str(err).find('could not detach kernel driver from interface') >= 0:
                print 'The in-kernel-HID driver has already been detached'
            elif str(err).find('Entity not found') >= 0:
                pass # suppress this error if already open
            else:
                print >> sys.stderr, err
        #self.handle.setConfiguration(self.conf)
        self.handle.claimInterface(self.intf) # Interface 0


    def close(self):
        try:
            self.handle.releaseInterface()
            #print ('Released device')
        except err:
            print >> sys.stderr, err


    def getManufactureName(self):
        return self.handle.getString(self.device.iManufacturer,30)


    def getProductName(self):
        return self.handle.getString(self.device.iProduct,30)


    
    def ReadPacket(self, RxCmd, RxLen=16):
        """ Reads command packet from the Delcom device.
            RxCom: The read command - For description of commands see the Delcom HID DataSheet
            RxLen: The read command lenght. Usally 8 or 16 (default is 16)
            Returns array of data
        """
        return(self.handle.controlMsg(0xA1, 0x01, RxLen, RxCmd, 0, self.TIMEOUT))
    


    def SendPacket(self, MajorCmd, MinorCmd, DataLSB, DataMSB, DataHID, DataExt):
        """ Writes the command packet to the Delcom device.
            For a description of commands see the Delcom HID DataSheet
            MajorCmd(1Byte): 101 for 8byte commands, 102 for 16byte commands
            MinorCmd(1Byte): Minor Command
            DataLSB(1Byte):
            DataLSB(1Byte):
            DataHID(4Byte):
            DataExt(8Bytes):
            Returns length written on success, else zero on error
        """
        sentbytes = 0
        if MajorCmd == 101 :
            data = struct.pack('BBBBL', MajorCmd, MinorCmd, DataLSB, DataMSB, DataHID)
            sentbytes = self.handle.controlMsg(0x21, 0x09, data, 0, 0x0000, self.TIMEOUT)
            
        if MajorCmd == 102 :
            data = struct.pack('BBBBLQ', MajorCmd, MinorCmd, DataLSB, DataMSB, DataHID, DataExt)
            sentbytes = self.handle.controlMsg(0x21, 0x09, data, 0, 0x0000, self.TIMEOUT)
                             
        return(sentbytes)

    def LEDControl(self, LED, MODE):
        """ Controls the LED on port 1
            LED = LED number (bitwise): 0=none, 0x1=LED1, 0x2=LED2,0x4=LED3, 0x8=LED4, 0xF=ALL LEDS
            MODE = LED CONTROL: 0=Off, 1=ON, 2=Blink
            Returns length written on success, else zero on error
            Examples:
                myDevice.LEDControl(myDevice.LEDALL, myDevice.LEDOFF)
                myDevice.LEDControl(myDevice.LED1, myDevice.LEDON)
                myDevice.LEDControl(myDevice.LED1, myDevice.LEDBLINK)
        """
        if(MODE==self.LEDON): # if MODE=ON
            MajorCmd, MinorCmd, DataLSB, DataMSB = 101, 20, LED, 0 # First turn LED flash mode off
            if( self.SendPacket(MajorCmd, MinorCmd, DataLSB,DataMSB,0,0) == 0):
                return(0)
            MajorCmd, MinorCmd, DataLSB, DataMSB = 101, 12, LED, 0 # Then turn LED On
            return( self.SendPacket(MajorCmd, MinorCmd, DataLSB,DataMSB,0,0) == 0)
        else :          # if MODE OFF OR FLASH
            MajorCmd, MinorCmd, DataLSB, DataMSB = 101, 20, LED, 0 # First turn LED flash mode off
            if( self.SendPacket(MajorCmd, MinorCmd, DataLSB,DataMSB,0,0) == 0):
                return(0)
            MajorCmd, MinorCmd, DataLSB, DataMSB = 101, 12, 0, LED # Then turn LED Off
            if( self.SendPacket(MajorCmd, MinorCmd, DataLSB,DataMSB,0,0) == 0):
                return(0)
        if(MODE==self.LEDBLINK): #if MODE = BLINK
            MajorCmd, MinorCmd, DataLSB, DataMSB = 101, 20, 0, LED # LED flash mode on
            if( self.SendPacket(MajorCmd, MinorCmd, DataLSB,DataMSB,0,0) == 0):
                return(0)
            
        return(8) # success
            

    def LEDPower(self, LED, POWER):
        """ Controls the LED on port 1
            LED = LED number (bitwise): 0=none, 0x1=LED1, 0x2=LED2,0x4=LED3, 0x8=LED4, 0xF=ALL LEDS
            POWER = LED POWER: 0-100   0=Off, 100=FULL POWER
            Returns length written on success, else zero on error
            Example: myDevice.LEDPower(myDevice.LED1,25) # sets LED1 to 25% power
        """
        MajorCmd, MinorCmd, DataLSB, DataMSB = 101, 34, LED, POWER
        if LED == self.LED1:
            DataLSB=0
        elif LED == self.LED2:
            DataLSB=1
        elif LED == self.LED3:
            DataLSB=2
        elif LED == self.LED4:
            DataLSB=3
        return(self.SendPacket(MajorCmd, MinorCmd, DataLSB,DataMSB,0,0))

    def DisplayInfo(self):
        """ Prints the firmware information
        """
        info = self.ReadPacket(104)
        print "Firmwar Version:", info[4], " Date:", info[5],"/",info[6],"/",info[7]+2000," FamilyCode:",info[0]
        

    def ReadPort0(self):
        # Reads port 0 value
        data = self.ReadPacket(100)
        return(data[0])
    
    def ReadPort1(self):
        # Reads port 1 value
        data = self.ReadPacket(100)
        return(data[1])
    
        
#--------------------------------------------------------------------#

#--------------------------------------------------------------------#
#------------------- CLASS: DeviceDescriptor ------------------------#
#--------------------------------------------------------------------#
class DeviceDescriptor(object):
    def __init__(self, vendor_id, product_id, interface_id):
        '''
        Constructor
        '''
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.interface_id = interface_id

    def getDevice(self):
        busses = usb.busses()
        for bus in busses:
            for device in bus.devices:
                if device.idVendor == self.vendor_id and \
                   device.idProduct == self.product_id:
                    return device
        return None







#------------------------------------------------------------------------------------------#
# example code - sample code on how to find, open, read, write and close the Delcom Device
#------------------------------------------------------------------------------------------#
def examplecode():
    print("Starting Delcom Python sample code...")
    myDevice = DelcomUSBDevice()        # Start the class and try and open the device
    if myDevice.find() == 0 :           # Test for find
        print "Failed to find the device. Program terminated."
        sys.exit(0)
    else :
        print "Delcom device found. VendorID:", myDevice.deviceDescriptor.product_id, " ProductID",myDevice.deviceDescriptor.vendor_id
    
    print "Open Device"
    myDevice.open()                     # Open the device
    myDevice.DisplayInfo()              # Display the device info
    print "Port0= ", myDevice.ReadPort0()        # Read port 0 value


    print "Turn all LEDs off"
    myDevice.LEDControl(myDevice.LEDALL, myDevice.LEDOFF)
    print "Turn LED1 on"
    myDevice.LEDControl(myDevice.LED1, myDevice.LEDON)      
    
    time.sleep(1)
    print "Turn LED1 off"
    myDevice.LEDControl(myDevice.LED1, myDevice.LEDOFF)      


    print "Turn LED2 on and blink it"
    myDevice.LEDControl(myDevice.LED2, myDevice.LEDBLINK)
    
    print "Close device"
    myDevice.close()        # You must close the device when your done, else you wont be able to open it again.
    print "All done................"



#------------------------------------------------------------------------------------------#
# Calls the examplecode() - Only calls this examplecode() if this is the main file.
# If imported into your code this examplecode() won't run
#------------------------------------------------------------------------------------------#
if __name__ == '__main__': examplecode()
        
