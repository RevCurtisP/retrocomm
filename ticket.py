#!/usr/bin/python
#Akron City Center Hotel Parking Time Calculator
#(C) 2014 Curtis F Kaylor

import datetime
import math
import string
from Tkinter import *

HELP_TEXT = """            Akron City Center Hotel Parking Time Calculator

This application calculates the number of hours charged back to the hotel
on stamped tickets based on the validated and printed time on the ticket.

Usage:
 Validated: Enter the exit time as printed on the ticket by the validator.
   Printed: Enter the entry time as printed on tthe ticket by the spitter.
     Total: Click to calculate and display total hours.
   
Time Entry:   
 Times (and optional dates) are entered using only digits. Entries are then
 formatted and displayed as a full date and time.

 Time may be entered as two or three digits representing the hour and minutes
 and must be in 24 hour format (which is how times are printed on tickets).

 The date is entered before (to the left of) the four digit time as a 
 one or two digit  day of the month, three or four digit month and day, 
 or six digit year, month, and day.

 If no date is entered, the today's date is assumed, unless the entered time
 is later then the current time, in which case yesterday's date is used.

 If the entered time/date is invalid, the entry is dimmed and the cursor 
 remains in the entry.

Keyboard Shortcuts:
       Tab: Move to the next widget. Tabbing to the total button calculates
            and displays the total hours as though it was clicked.
 Shift-Tab: Move to the previous widget.
    Return: Move to the next widget. Unlike Tab, Return does not wrap around.
   Up/Down: Move between Validated and Printed time entries.
    Escape: Clear all entries and start over.
        F1: Display this help screen.
    
Numeric Keypad:
 The numeric keypad is supported in both numeric and cursor mode. The Enter, 
 Asterisk (*), and Slash (/) keys perfom the same functions as Return,
 Escape, and F1 keys, respectively.
 
 The Plus (+) key performs a Backspace, and the Minus (+) key clears the
 current entry.
 
 The keys M, J, K L, U, I, O are interpeted as the digits 0 through 6
 allowing keypad type entry on notebook computers without using Num-Lock.
 
 In addition, the Spacebar acts the same as the Escape key.

"""

class HelpWindow(Toplevel):

  #set function to be called when window closes
  def setCallback(self, callback):
    self.__callback = callback
    
  #close window
  def close(self, event=None):
    if self.__callback: self.__callback()
    self.destroy()
    
  #scroll down one line  
  def down(self, event=None):
    self.text.yview(SCROLL, 1, UNITS)
    
  #scroll to end
  def end(self, event=None):
    self.text.yview(MOVETO, 1.0)

  #scroll to beginning
  def home(self, event=None):
    self.text.yview(MOVETO, 0.0)
    
  #scroll down one page  
  def next(self, event=None):
    self.text.yview(SCROLL, 1, PAGES)

  #scroll up one page  
  def prior(self, event=None):
    self.text.yview(SCROLL, -1, PAGES)
    
  #scroll up one line
  def up(self, event=None):
    self.text.yview(SCROLL, -1, UNITS)
    
  #create help window with specified help text
  def __init__(self, text):
    #create help window
    Toplevel.__init__(self)
    #initialize callback function
    self.__callback = None
    #set window to disallow resizing
    self.resizable(0,0)
    #create text box
    self.text = Text(self)
    self.text.grid(row=0, column=0)
    #create scrollbar widget and bind to text box
    self.scroll = Scrollbar(self, command=self.text.yview)
    self.scroll.grid(row=0, column=1, sticky="ns")
    #bind text box to scrollbar
    self.text.config(yscrollcommand=self.scroll.set)
    #create button and bind to close function
    self.button = Button(self, text="Close", command=self.close)
    self.button.grid(row=1,column=0)
    #set key bindings
    self.button.bind_all('<KeyPress-Escape>', self.close)
    self.button.bind_all('<KeyPress-KP_Multiply>', self.close)
    self.scroll.bind_all('<KeyPress-Down>', self.down)
    self.scroll.bind_all('<KeyPress-KP_Down>', self.down)
    self.scroll.bind_all('<KeyPress-Up>', self.up)
    self.scroll.bind_all('<KeyPress-KP_Up>', self.up)
    self.scroll.bind_all('<KeyPress-Next>', self.next)
    self.scroll.bind_all('<KeyPress-KP_Next>', self.next)
    self.scroll.bind_all('<KeyPress-Prior>', self.prior)
    self.scroll.bind_all('<KeyPress-KP_Prior>', self.prior)
    self.scroll.bind_all('<KeyPress-Home>', self.home)
    self.scroll.bind_all('<KeyPress-KP_Home>', self.home)
    self.scroll.bind_all('<KeyPress-End>', self.end)
    self.scroll.bind_all('<KeyPress-KP_End>', self.end)
    #insert help text into text box and make read only
    self.text.insert(INSERT,text)
    self.text.config(state=DISABLED)
    #move focus to help window
    self.focus_force()

#Date/Time Entry Widget:
# only digits are allowed, entry is validated and formatted
class DateTimeEntry(Entry):

  #generate a BackSpace key press
  def __backspace(self, event=None):
    self.event_generate('<KeyPress-BackSpace>')
    return 'break'

  #generate an Escape key press
  def __escape(self, event=None):
    self.event_generate('<KeyPress-Escape>')
    return 'break'

  #generate an F1 key press
  def __help(self, event=None):
    self.event_generate('<KeyPress-F1>')
    return 'break'

  #Key Binding:
  # Allow only digits in entry
  # Map Keypad Plus, Minus, Asterisk, and Slash keys
  # Map Notebook Num-Lock keys
  def __filterKeys(self, event):
    c = event.char
    if len(c) == 0: return
    if c in ['+', '=']: return self.__backspace()
    if c in ['-', '_']: return self.clear()
    if c in ['*', ' ']: return self.__escape()
    if c in '/': 
      return self.__help()
    s = self.get()
    i = "MJKLUIO".find(c.upper()) if c else -1
    if i > -1 :
      if self.selection_present():
        self.delete(self.index("sel.first"), self.index("sel.last"))
      self.insert(INSERT, str(i))
      return 'break'
    elif c >= " " and c <> chr(127):
      if not c.isdigit() or len(s)>9:
        self.bell()
        return 'break'
    return

  #get Default Date, based on entered hours and minutes
  def __defDate(self, hr, mi):
    today = datetime.datetime.today()
    yesterday = today - datetime.timedelta(1)
    entered = datetime.time(hr, mi)
    current = datetime.datetime.now().time() 
    if entered >= current:
      defdate = yesterday
    else:
      defdate = today
    if self.debug:
      print "today", today
      print "yday ", yesterday
      print "enter", entered
      print ".00011*curr ", current
      print "def  ", defdate
    return defdate
  
  #Split YYMMDD into year, month, day, replacing blanks with current period
  def __splitDate(self, ds, defdt):
    cs = str(int(defdt.year/100)) #Current Century
    ys, ms, ds = ds[:2], ds[2:4], ds[4:6]
    yi = defdt.year  if ys == "  " else int(cs+ys)
    mi = defdt.month if ms == "  " else int(ms)
    di = defdt.day   if ds == "  " else int(ds)
    return yi, mi, di

  #Replace Entry contents with specified text
  def __set(self, text):
    self.delete(0,END)
    self.insert(0,text)

  #FocusIn binding to restore entered text and select all
  def __restoreText(self, event):
    self.__set(self.__text)
    self.selection_range(0,END)
    return

  #FocusOut binding to validate and format entry
  def __formatText(self, event):
    f = None    #Formated Date/Time entry
    dt = None   #Datetime object corresponding to entry
    self.__text = self.get()
    if self.__text == "":
      f = ""
    elif len(self.__text) in [3, 4, 5, 6, 7, 8, 10]:
      dts = string.rjust(self.__text, 10)
      try:
        ds = dts[:6] #date portion of entry
        ts = dts[6:] #time portion of entry
        hr, mi = int(ts[:2]), int(ts[2:]) #extract hours and minutes
        defdt = self.__defDate(hr, mi)  #get default date
        yr, mo, dy = self.__splitDate(ds, defdt) #extract year, month, and day
        #build datetime object
        dt = datetime.datetime(yr, mo, dy, hr, mi)
        #build formatted date string
        f = "{0:04d}-{1:02d}-{2:02d} {3:02d}:{4:02d}".format(yr, mo, dy, hr, mi)
      except Exception as x:
        if __debug__: print x.message
    if f == None:
      #Invalid entry: set background and keep focus
      self.bell() #May not work on all systems
      self.config(background=self.cget('disabledbackground'))
      self.focus()
    else:
      #Valid entry: display formatted text and clear background
      self.__set(f)
      self.config(background=self.__background)
    self.datetime = dt
    return

  #Clear entry: delete all text and clear datetime property
  def clear(self):
    self.__text = ""
    self.__set(self.__text)
    self.datetime = None
    return 'break'

  #Create DateTimeEntry widget in specified container widget
  def __init__(self, master):
    self.debug = False
    #Initialize Widget
    Entry.__init__(self, master)
    self.config(justify=RIGHT, width=14)
    #Set Private Properties
    self.__background = self.cget('background')
    #Set Event Bindings
    self.bind("<Key>", self.__filterKeys)
    self.bind("<FocusIn>", self.__restoreText)
    self.bind("<FocusOut>", self.__formatText)
    #Set Initial Values
    self.clear()
    return

#Display: Read-Only Entry Widget
class Display(Entry):

  #Create DisplayEntry widget in specified container widget
  def __init__(self, master):
    #Initialize 
    Entry.__init__(self, master)
    self.config(justify=RIGHT, state=DISABLED, width=9)
    self.config(disabledforeground=self.cget('foreground'))
    #Set Private Properties
    self.__state = self.cget('state')
    return

  ##Set Displayed Text
  def set(self, text):
    self.config(state=NORMAL)
    self.delete(0,END)
    self.insert(0,text)
    self.config(state=self.__state)
    return

  #Clear Displayed Text
  def clear(self):
    self.set("")
    return

#Master Date/Time Entry and Calculation Window
class TicketWindow(Tk):
  
  __COLUMNS = 3

  #Generate Tab key press
  def __tab(self, event):
    event.widget.event_generate('<KeyPress-Tab>')
    return 'break'

  #Generate Shift-Tab key press
  def __backtab(self, event):
    event.widget.event_generate('<Shift-KeyPress-Tab>')
    return 'break'

  #Create a Label in column 0 of the specified row
  def __label(self, text="", row=0):
    label = Label(self, justify=CENTER, text=text)
    label.grid(row=row, column=0, columnspan=self.__COLUMNS)
    return label

  #Create a Label and DateEntry in the specified row
  def __entry(self, label="", row=0):
    _label = Label(self, text=label)
    _label.grid(row=row, column=0, sticky=E)
    _entry = DateTimeEntry(self)
    _entry.label = _label
    _entry.grid(row=row, column=1, columnspan=self.__COLUMNS-1)
    _entry.bind('<KeyPress-Return>', self.__tab)
    _entry.bind('<KeyPress-KP_Enter>', self.__tab)
    return _entry

  #Create a Button in the specified column and row
  def __button(self, text="", row=0, column=0):
    _button = Button(self, text=text)
    _button.grid(row=row, column=column, sticky=E)
    #when button is clicked, force it to focus
    _button.config(command=lambda: _button.focus())
    return _button

  #Create a Label and Display in the specified row
  def __display(self, label="", row=0, column=0):
    _display = Display(self)
    _display.grid(row=3, column=1, sticky=W+E)
    _label = Label(self, justify=LEFT, text=label)
    _label.grid(row=row, column=column, sticky=W)
    _display.label = _label
    return _display

  #Calculate and display total hours
  def __calc(self, event):
    vdt = self.validated.datetime
    pdt = self.printed.datetime
    if vdt and pdt:
      delta = vdt - pdt if vdt > pdt else pdt - vdt
      seconds = delta.days * 24.0 * 3600 + delta.seconds
      hours = math.ceil(seconds/3600)
      text = str(int(hours)) if hours > 1 else "GP"
      if self.debug:
        print "start", pdt
        print "end  ", vdt
        print "delta", delta
        print "days", delta.days
        print "secs", delta.seconds
        print "total ", seconds
        print "hours", hours
    else:
      text = ""
    self.total.set(text)
    return

  #Clear all entries and total
  def __clear(self, event=None):
    self.validated.clear()
    self.printed.clear()
    self.total.clear()
    self.validated.focus()
    return 'break'

  #Open a help window
  def __help(self, event=None):
    if self.debug: print "help"
    if self.help == None:
      self.help = HelpWindow(HELP_TEXT)
      self.help.setCallback(self.helpClosed)

  #Callback: executed by Help Window when it closes
  def helpClosed(self):
    if self.debug: print "help closed"
    self.help = None

  #Create Ticket Window
  def __init__(self):
    Tk.__init__(self)
    self.debug = False
    self.title("ticket")
    self.banner = self.__label(text="Hotel Ticket Time Calculator", row=0)
    self.validated = self.__entry(label="Validated", row=1)
    self.validated.bind('<KeyPress-Down>', self.__tab)
    self.validated.bind('<KeyPress-KP_Down>', self.__tab)
    self.printed = self.__entry(label="Printed", row=2)
    self.printed.bind('<KeyPress-Up>', self.__backtab)
    self.printed.bind('<KeyPress-KP_Up>', self.__backtab)
    self.button = self.__button(text="Total", row=3, column=0)
    self.button.bind("<FocusIn>", self.__calc)
    self.total = self.__display(row=3, column=1)
    self.total.bind_all('<KeyPress-Escape>', self.__clear)
    self.total.bind_all('<KeyPress-KP_Multiply>', self.__clear)
    self.total.bind_all('<space>', self.__clear)
    self.total.bind_all('<KeyPress-F1>', self.__help)
    self.total.bind_all('<KeyPress-KP_Divide>', self.__help)
    self.__clear()
    self.helpClosed()
    self.mainloop()

if __name__ == '__main__':
  ticketWindow = TicketWindow()

