'''
Created on 19 Jan 2014

Add some notes here about the choice of UI architecture, in particular TreeView


@author: MBradley
'''

from Tkinter import *
from ttk import *
 

from model.race import RaceManager

class StartLineFrame(Frame):
    '''
    classdocs
    '''


    def __init__(self,master=None,backgroundColour=None,fullScreen=False,fontSize=16):
        '''
        Constructor
        '''
        self.tk = Tk()
        self.fontSize=fontSize
        
        self.tk.attributes('-fullscreen',fullScreen)
        Frame.__init__(self, self.tk)
        self.backgroundColour=backgroundColour
        self.grid(sticky=N+S+E+W)
        self.createWidgets()

        
    def createWidgets(self):
        
        top=self.winfo_toplevel()                
        top.rowconfigure(0, weight=1)            
        top.columnconfigure(0, weight=1)
        
        style = Style()
        #style.theme_use('winnative')
        style.configure('.', font=('Helvetica',self.fontSize))
        style.configure('Treeview',rowheight=30)
        style.configure('TButton')
        
        
    
        
        self.fleetsTreeView = Treeview(self,
                                      columns=["startTime","startTimeSeconds","status"],
                                      
                                      selectmode="browse",
                                      height=5)
        
        ysb = Scrollbar(self, orient='vertical', command=self.fleetsTreeView.yview)
        xsb = Scrollbar(self, orient='horizontal', command=self.fleetsTreeView.xview)
        self.fleetsTreeView.heading("#0"  , text='Fleet', anchor=W)
        #self.fleetsTreeView.column("#0", width=350)
        self.fleetsTreeView.heading("startTime",text='Start time', anchor=W)
        self.fleetsTreeView.column("startTime",width=125)
        self.fleetsTreeView.heading("startTimeSeconds",text='Start time seconds',anchor=W)
        self.fleetsTreeView.column("startTimeSeconds",width=125)
        self.fleetsTreeView.heading("status",text='Status', anchor=W)
        self.fleetsTreeView.configure(yscroll=ysb.set, xscroll=xsb.set)
        self.fleetsTreeView.grid(row=0,column=0,columnspan=2,rowspan=2,sticky=N+S+E+W)
        ysb.grid(row=0, column=2, sticky=N+S, rowspan=2)
        xsb.grid(row=2, column=0, columnspan=2,sticky=W+E)
        
        # add fleet button
        self.addFleetButton = Button(self,
                                    text="Add fleet")
        self.addFleetButton.grid(row=3,
                                column=0,
                                sticky=W+E+N+S,
                                   #ipady=20
                                   )
        
        
        # remove fleet button
        self.removeFleetButton = Button(self,
                                        text="Remove fleet",state=DISABLED)
        self.removeFleetButton.grid(row=4,
                                   column=0, 
                                   sticky=W+E+N+S,
                                   #ipady=20
                                   )
        
        # start race sequence with warning
        self.startRaceSequenceWithWarningButton = Button(self,
                                        text="F Flag Start",state=DISABLED)
        self.startRaceSequenceWithWarningButton.grid(row=3,
                                                     column=1,
                                                     sticky=W+E+N+S,
                                                     #ipady=20
                                                     )
        
        # start race sequence without warning
        self.startRaceSequenceWithoutWarningButton = Button(self,
                                        text="Class Flag Start",state=DISABLED)
        self.startRaceSequenceWithoutWarningButton.grid(row=4,
                                                        column=1,
                                                        sticky=W+E+N+S,
                                                        #ipady=20
                                                        )
        
        # general recall button
        self.generalRecallButton = Button(self,
                                        text="General recall",state=DISABLED)
        self.generalRecallButton.grid(row=5,
                                      column=1,
                                      sticky=W+E+N+S,
                                      #ipady=20
                                      )
        
        # abandon sequence button
        self.abandonStartRaceSequenceButton = Button(self,
                                          text="Abandon start",state=DISABLED)
        self.abandonStartRaceSequenceButton.grid(row=5,
                                      column=0,
                                      sticky=W+E+N+S,
                                      #ipady=20
                                      )
        
        
            
        
        #
        # Finish list (implemented using ttk Treeview
        #
        
        self.finishTreeView = Treeview(self,columns=["fleet","elapsedTimeSeconds"],style="Treeview")
        ysb = Scrollbar(self, orient='vertical', command=self.finishTreeView.yview)
        xsb = Scrollbar(self, orient='horizontal', command=self.finishTreeView.xview)
        self.finishTreeView.configure(yscroll=ysb.set, xscroll=xsb.set)
        
        
        
        self.finishTreeView.heading("#0",text='Finish time',anchor=W)
        self.finishTreeView.heading("fleet",text="Fleet", anchor=W)
        self.finishTreeView.heading("elapsedTimeSeconds",text="Elapsed time", anchor=W)
        
        self.finishTreeView.grid(row=0, column=3, rowspan=6,sticky=W+E+N+S)
        ysb.grid(row=0,column=4,rowspan=6,stick=N+S)
        xsb.grid(row=6,column=3,sticky=E+W)
        #
        # Fleet buttons. We create six fleet buttons. The buttons live in a panel
        # that fills a whole column.
        #
        self.fleetButtonFrame = Frame(self)
        self.fleetButtonFrame.configure(width=150)
        self.fleetButtonFrame.grid(row=0,column=5,sticky=W+E+N+S,rowspan=6)
        
        #
        # Gun and finish
        #
        self.gunAndFinishButton = Button(self, text="Gun\nand\nfinish")
        self.gunAndFinishButton.grid(row=0,column=6,sticky=W+E+N+S)
        
        #
        # gun button
        #
        self.gunButton = Button(self,
                                    text="Gun")
        self.gunButton.grid(row=1,column=6,sticky=W+E+N+S)
        
        #
        # exit button
        #
        self.exitButton = Button(self,
                                 text="Quit")
        self.exitButton.grid(row=5,column=6,sticky=W+E+N+S)
        
        
        #
        # clock
        #
        self.clockStringVar = StringVar(self,value="00:00:00")
        clockLabel = Label(self,textvariable=self.clockStringVar)
        clockLabel.grid(row=7,column=5)
        
        #
        # EasyDaqRelay connection status label
        #
        self.connectionStatus = StringVar(self,value="")
        connectionStatusLabel = Label(self,textvariable=self.connectionStatus,justify=LEFT,anchor=W)
        connectionStatusLabel.grid(row=7,column=0,columnspan=2,sticky=E+W)
        
        #
        # Gun queue label
        #
        self.gunQueueCount = StringVar(self,value="Gun Q: 0")
        gunQueueCountLabel = Label(self,textvariable=self.gunQueueCount)
        gunQueueCountLabel.grid(row=7,column=6)
        
        
        
        #
        # configure how the grid should resize. For now, we'll just configure the first
        # row and first column to resize
        #
        Grid.rowconfigure(self,0,weight=1)
        Grid.rowconfigure(self,1,weight=1)
        # not row 2, this is a scroll bar
        Grid.rowconfigure(self,3,weight=1)
        Grid.rowconfigure(self,4,weight=1)
        Grid.rowconfigure(self,5,weight=1)
        
        Grid.columnconfigure(self,0,weight=1)
        Grid.columnconfigure(self,1,weight=1)
        # not column 2, this is a scroll bar
        Grid.columnconfigure(self,3,weight=1)
        # not column 4, this is a scroll bar
        Grid.columnconfigure(self,6,weight=1)
        
        
        # tell the frame to lay itself out
        
        self.grid()
        
    #
    # dynamically create a fleet button and add to our fleet frame
    #
    def createFleetButton(self,fleetName,fleetIndex):
        button = Button(self.fleetButtonFrame,text=fleetName,state=DISABLED)
        button.grid(row=fleetIndex, column=0,sticky=W+E+N+S)
        Grid.rowconfigure(self.fleetButtonFrame,fleetIndex,weight=1)
        return button
         
        
        
        
    def enableGeneralRecallButton(self):
        self.generalRecallButton['state']=NORMAL
    
    def disableGeneralRecallButton(self):
        self.generalRecallButton['state']=DISABLED
        
    def enableAddFleetButton(self):
        self.addFleetButton['state']=NORMAL
        
    def disableAddFleetButton(self):
        self.addFleetButton['state']=DISABLED
        
    
    def enableRemoveFleetButton(self):
        self.removeFleetButton['state']=NORMAL
        
    def disableRemoveFleetButton(self):
        self.removeFleetButton['state']=DISABLED
        
    def disableStartRaceSequenceWithWarningButton(self):
        self.startRaceSequenceWithWarningButton['state'] = DISABLED
        
    def disableStartRaceSequenceWithoutWarningButton(self):
        self.startRaceSequenceWithoutWarningButton['state'] = DISABLED
        
    def enableStartRaceSequenceWithWarningButton(self):
        self.startRaceSequenceWithWarningButton['state'] = NORMAL
        
    def enableStartRaceSequenceWithoutWarningButton(self):
        self.startRaceSequenceWithoutWarningButton['state'] = NORMAL
        
    def disableAbandonStartRaceSequenceButton(self):
        self.abandonStartRaceSequenceButton['state'] = DISABLED
        
    def enableAbandonStartRaceSequenceButton(self):
        self.abandonStartRaceSequenceButton['state'] = NORMAL
        
class AddFleetDialog:
    def __init__(self, parent, fleetNamesList,fontSize=16):
        self.top = Toplevel(parent)
        self.frame = Frame(self.top)
        self.frame.pack(fill=BOTH,expand=True)
        self.fontSize = fontSize
        self.fleetNamesList = fleetNamesList
        self.fleetName = None
        self.createWidgets()
        
        
        
        
    def createWidgets(self):
        style = Style()
        style.configure('.', font=('Helvetica',self.fontSize))
        style.configure('Treeview',rowheight=30)
        
        label = Label(self.frame, text='Choose from the list:')
        label.pack()
        
        self.fleetNamesListBox = Treeview(self.frame,
                                         selectmode="browse")
        self.fleetNamesListBox.column("#0", width=400)
        
        self.fleetNamesListBox.pack(fill=BOTH,expand=True)
        
        # we use the name of the fleet as the list id. Should be fine so long as there are no duplicates
        for fleetName in self.fleetNamesList:
            self.fleetNamesListBox.insert(parent="",index="end",text=fleetName,iid=fleetName)
            
        self.fleetNamesListBox.bind('<<TreeviewSelect>>',self.fleetNameListItemSelected)
        self.fleetNamesListBox.bind("<Double-1>", self.fleetNameDoubleClicked)
    
        label = Label(self.frame, text='or type in your own', anchor=W)
        label.pack()
        
        
        self.fleetNameVariable = StringVar()
        self.fleetNameLabel = Entry(self.frame,textvariable = self.fleetNameVariable)
        self.fleetNameLabel.pack(fill=BOTH,expand=True)
        
        
        
        self.cancelButton = Button(self.frame,text="Cancel",command=self.cancelClicked)
        self.cancelButton.pack()
        self.okButton = Button(self.frame,text="OK",command=self.okClicked)
        self.okButton.pack()
        
    def fleetNameListItemSelected(self,event):
        
        
        # note that we set the iid of each item in the list to be the name. Very simple.
        selectedFleetName = self.fleetNamesListBox.selection()[0]
        self.fleetNameVariable.set(selectedFleetName)
    
    def fleetNameDoubleClicked(self,event):
        selectedFleetName = self.fleetNamesListBox.selection()[0]
        self.fleetNameVariable.set(selectedFleetName)
        self.fleetName=self.fleetNameVariable.get()
        self.top.destroy()
        
    
    def okClicked(self):
        self.fleetName=self.fleetNameVariable.get()
        self.top.destroy()
        
    def cancelClicked(self):
        self.fleetName=None
        self.top.destroy()
    
    def show(self):

        self.focus_set()
        self.grab_set()
        self.transient(self.parent)
        self.wait_window(self)
    