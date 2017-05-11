#!/usr/bin/python
#Cascade Parking Garage Shift Report

import time
from Tkinter import *

def center(win):
  win.update_idletasks()
  frm_width = win.winfo_rootx() - win.winfo_x()
  win_width = win.winfo_width() + (frm_width*2)
  titlebar_height = win.winfo_rooty() - win.winfo_y()
  win_height = win.winfo_height() + (titlebar_height + frm_width)
  x = (win.winfo_screenwidth() / 2) - (win_width / 2)
  y = (win.winfo_screenheight() / 2) - (win_height / 2)
  geom = (win.winfo_width(), win.winfo_height(), x, y) # see note
  win.geometry('{0}x{1}+{2}+{3}'.format(*geom))

def nextColumn(container, columnspan=1):
  column = container.__dict__.get('currentColumn',0)
  container.currentColumn = column + columnspan
  return column

def nextRow(container):
  row = container.__dict__.get('currentRow',0)
  container.currentRow = row + 1
  container.currentColumn = 0
  return row

class Banner(Label):
  def __init__(self, master, text, columnspan=1):
    Label.__init__(self, master)
    self.config(text=text, borderwidth=1, justify=CENTER, relief=RIDGE)
    self.grid(row=nextRow(master), column=0, columnspan=columnspan, sticky=W+E)
    return

class Checkbox(Checkbutton):
  def __backtab(self, event):
    event.widget.event_generate('<Shift-KeyPress-Tab>')
    return 'break'
  def __tab(self, event):
    event.widget.event_generate('<KeyPress-Tab>')
    return 'break'
  def __init__(self, master, **arg):
    Checkbutton.__init__(self, master, arg)
    self.__checked = IntVar()
    self.config(variable=self.__checked)
    self.bind('<KeyPress-Return>', self.__tab)
    self.bind('<KeyPress-KP_Enter>', self.__tab)
    self.bind('<KeyPress-Down>', self.__tab)
    self.bind('<KeyPress-KP_Down>', self.__tab)
    self.bind('<KeyPress-Up>', self.__backtab)
    self.bind('<KeyPress-KP_Up>', self.__backtab)

    return
  def checked(self):
    return self.__checked.get()

class ColumnLabel(Label):
  def __init__(self, master, text):
    Label.__init__(self, master)
    self.config(text=text)
    self.grid(row=master.currentRow, column=nextColumn(master), sticky=W+E)
    return

class FloatEntry(Entry):

  def getfloat(self, default=None):
    s = self.get()
    d = s.find(".") > -1
    f = default if s == "" else float(self.get())
    if self.autodecimal and f and not d: f /= 100
    return f

  def getint(self, default=None):
    f = self.getfloat(default)
    i = None if f==None else int(f)
    return i

  def set(self, s):
    self.config(state=NORMAL)
    self.delete(0, END)
    self.insert(0, s)
    self.config(state=self.__state)
    return

  def setfloat(self, f, fmt="{:0.2f}"):
    s = "" if f == None else fmt.format(f)
    self.set(s)
 
  def setint(self, i, fmt="{:0d}"):
    s = "" if i == None else fmt.format(i)
    self.set(s)
    return

  def clear(self, event=None):
    self.setfloat(None)
    return 'break'
 
  def decrement(self, event=None):
    i = self.getfloat(0)
    d = .25 if self.autodecimal else 1
    i = i - d if i > d else None
    self.setfloat(i)
    return 'break'
 
  def increment(self, event=None):
    i = self.getfloat(0)
    d = .25 if self.autodecimal else 1
    self.setfloat(i+d)
    return 'break'
 
  def __filterKeys(self, event):
    c = event.char
    if c in [' ', '*']: return self.clear()
    #if c in ['-', '_']: return self.decrement()
    if c in ['+', '=']: return self.increment()
    s = self.get()
    l = self.cget("width")
    if c >= " " and c <> chr(127):
      if len(s)>l-1: 
        c = None
      elif c in ['-', '_']:
        if len(s): c = None;
      elif c == ".":
        if c in s: c = None
      elif not c.isdigit(): 
        c = None
    if c == None: 
      self.bell()
      return 'break'
    return

  def __format(self, event):
    f = self.getfloat()
    self.setfloat(f)
    return
    
  def __restore(self, event):
    s = self.get()
    s = s.rstrip("0")
    s = s.rstrip(".")
    self.set(s)
    return

  def __backtab(self, event):
    event.widget.event_generate('<Shift-KeyPress-Tab>')
    return 'break'
    
  def __tab(self, event):
    event.widget.event_generate('<KeyPress-Tab>')
    return 'break'
    
  def __init__(self, master, value=None, readonly=False, label=None, autodecimal=False):
    Entry.__init__(self, master)
    self.autodecimal = autodecimal
    self.config(justify=RIGHT, width=9)
    self.config(disabledforeground=self.cget('foreground'))
    if readonly: self.config(state=DISABLED)
    self.__state = self.cget("state")
    self.setfloat(value)
    self.bind("<Key>", self.__filterKeys)
    self.bind('<KeyPress-Return>', self.__tab)
    self.bind('<KeyPress-KP_Enter>', self.__tab)
    self.bind('<KeyPress-Down>', self.__tab)
    self.bind('<KeyPress-KP_Down>', self.__tab)
    self.bind('<KeyPress-Up>', self.__backtab)
    self.bind('<KeyPress-KP_Up>', self.__backtab)
    self.bind('<KeyPress-KP_Add>', self.increment)
    self.bind('<KeyPress-KP_Subtract>', self.decrement)
    self.bind('<KeyPress-KP_Multiply>', self.clear)
    self.bind("<FocusIn>", self.__restore)
    self.bind("<FocusOut>", self.__format)
    if label:
      row = nextRow(master)
      self.label = Label(master, text=label)
      self.label.grid(row=row, column=nextColumn(master), sticky=E)
    else:
      row = master.currentRow
    self.grid(row=row, column=nextColumn(master))
    return

class IntegerEntry(Entry):

  def getint(self, default=None):
    s = self.get()
    i = default if s == "" else int(self.get())
    return i
 
  def set(self, s):
    self.config(state=NORMAL)
    self.delete(0, END)
    self.insert(0, s)
    self.config(state=self.__state)
    return
 
  def setint(self, i, fmt="{:0d}"):
    s = "" if i == None else fmt.format(i)
    self.set(s)
    return

  def clear(self, event=None):
    self.setint(None)
    return 'break'
 
  def decrement(self, event=None):
    i = self.getint(0)
    i = i - 1 if i > 1 else None
    self.setint(i)
    return 'break'
 
  def increment(self, event=None):
    i = self.getint(0)
    self.setint(i+1)
    return 'break'
 
  def __format(self, event=None):
    i = self.getint()
    if self.__plusminus:
      i = self.__plusminus if i==None else i + self.__plusminus
    self.setint(i)
    return

  def __unformat(self, event=None):
    i = self.getint()
    if self.__plusminus and i <> None:
      i -= self.__plusminus
      if i == 0: i = None
    self.setint(i)
    return

  def setPlusMinus(self, plusminus):
    self.__unformat()
    self.__plusminus = plusminus
    self.__format()

  def __filterKeys(self, event):
    c = event.char
    if c in [' ', '*']: return self.clear()
    if c in ['-', '_']: return self.decrement()
    if c in ['+', '=']: return self.increment()
    s = self.get()
    l = self.cget("width")
    if c >= " " and c <> chr(127):
      if not c.isdigit() or len(s)>l-1:
        self.bell()
        return 'break'
    return

  def __backtab(self, event):
    event.widget.event_generate('<Shift-KeyPress-Tab>')
    return 'break'

  def __tab(self, event):
    event.widget.event_generate('<KeyPress-Tab>')
    return 'break'
    
  def __init__(self, master, label=None, readonly=False):
    '''If a label text is specified, create label and entry and move to 
       next row, otherwise create entry and move to next column'''
    Entry.__init__(self, master)
    self.__plusminus = 0
    self.config(justify=RIGHT, width=5)
    self.config(disabledforeground=self.cget('foreground'))
    if readonly: self.config(state=DISABLED)
    self.__state = self.cget("state")
    self.bind("<Key>", self.__filterKeys)
    self.bind('<KeyPress-Return>', self.__tab)
    self.bind('<KeyPress-KP_Enter>', self.__tab)
    self.bind('<KeyPress-Down>', self.__tab)
    self.bind('<KeyPress-KP_Down>', self.__tab)
    self.bind('<KeyPress-Up>', self.__backtab)
    self.bind('<KeyPress-KP_Up>', self.__backtab)
    self.bind('<KeyPress-KP_Add>', self.increment)
    self.bind('<KeyPress-KP_Subtract>', self.decrement)
    self.bind('<KeyPress-KP_Multiply>', self.clear)
    self.bind("<FocusIn>", self.__unformat)
    self.bind("<FocusOut>", self.__format)
    if label:
      row = nextRow(master)
      self.label = Label(master, text=label)
      self.label.grid(row=row, column=nextColumn(master), sticky=E)
    else:
      row = master.currentRow
    self.grid(row=row, column=nextColumn(master))
    return

class TextDisplay(Entry):

  def __init__(self, master, text, columnspan=1, justify=CENTER, width=None, label=None):
    if label:
      row = nextRow(master)
      self.label = Label(master, text=label)
      self.label.grid(row=row, column=nextColumn(master), sticky=E)
    else:
      row = master.currentRow
    column = nextColumn(master, columnspan)
    Entry.__init__(self, master)
    self.config(justify=justify)
    self.config(disabledforeground=self.cget('foreground'))
    if width: self.config(width=width)
    self.insert(0, text)
    self.config(state=DISABLED)
    self.grid(row=row, column=column, columnspan=columnspan, sticky=E+W)
    return

class CashDrop(Frame):

  def addTotal(self, amount):
    total = self.total
    if amount:
      total = amount if total == None else total + amount
    self.total = total

  def __calc(self, event):
    self.total = None
    self.addTotal(self.coinAmount.getfloat())
    self.addTotal(self.onesAmount.getfloat())
    self.addTotal(self.otherAmount.getfloat())
    self.cashAmount.setfloat(self.total)
    self.addTotal(self.checkAmount.getfloat())
    self.totalAmount.setfloat(self.total)
    if self.totfn: self.totfn()
    return
      
  def __init__(self, totfn=None):
    Frame.__init__(self)
    self.config(borderwidth=2, relief=RIDGE)
    self.label = Banner(self, "Cash Drop Slip", columnspan=2)
    self.coinAmount = FloatEntry(self, label="Coin", autodecimal=True)
    self.coinAmount.bind("<FocusOut>", self.__calc, add='+')
    self.onesAmount = FloatEntry(self, label="Ones")
    self.onesAmount.bind("<FocusOut>", self.__calc, add='+')
    self.otherAmount = FloatEntry(self, label="Other")
    self.otherAmount.bind("<FocusOut>", self.__calc, add='+')
    self.cashAmount = FloatEntry(self, label="Cash", readonly=True)
    self.cashAmount.bind("<FocusOut>", self.__calc, add='+')
    self.checkAmount = FloatEntry(self, label="Checks", autodecimal=False)
    self.checkAmount.bind("<FocusOut>", self.__calc, add='+')
    self.totalAmount = FloatEntry(self, label="Total", readonly=True)
    self.totalAmount.bind("<FocusOut>", self.__calc, add='+')
    self.creditAmount = FloatEntry(self, label="Credit", autodecimal=False)
    self.creditAmount.bind("<FocusOut>", self.__calc, add='+')
    self.totfn = totfn
    return

  def getTotalDollars(self):
    cash = self.totalAmount.getfloat()
    credit = self.creditAmount.getfloat()
    if cash == None and credit == None: return None
    if cash == None: cash = 0
    if credit == None: credit = 0
    return cash + credit

class DisplayDate(Frame):

  def __init__(self, totfn=None):
    Frame.__init__(self)
    self.config(borderwidth=2, relief=RIDGE )
    text = time.strftime('%m-%d-%y')
    self.dateDisplay = TextDisplay(self, text, width=9, label="Date")
    return

class Spacer(Frame):

  def __init__(self, fill=None):
    Frame.__init__(self)
    self.label = Label(self, text=' ')
    self.label.pack(fill=fill, expand=(fill<>None))

class TicketCount(Frame):

  def __calc(self, event):
    bs = self.beginCount.get()
    es = self.endCount.get()
    ts = ""
    if bs and es:
      bi = int(bs)
      ei = int(es)
      if ei > bi:
        ts = str(ei-bi)
      else:
        self.bell()
    self.totalCount.set(ts)
    if self.totfn: self.totfn()
    return
      
  def __init__(self, totfn=None):
    Frame.__init__(self)
    self.config(borderwidth=2, relief=RIDGE)
    self.label = Banner(self, "Transaction Count", columnspan=2)
    self.beginCount = IntegerEntry(self, label="Start #")
    self.beginCount.bind("<FocusOut>", self.__calc)
    self.endCount = IntegerEntry(self, label="End #")
    self.endCount.bind("<FocusOut>", self.__calc)
    self.totalCount = IntegerEntry(self, label="Total", readonly=True)
    self.totfn = totfn
    return

  def getTotalTickets(self):
    return self.totalCount.getint()

class NoRings(Frame):

  def __calc(self, event):
    self.total = self.noRings.getint()
    if self.totfn: self.totfn()
    return    
    
  def __init__(self, totfn=None):
    Frame.__init__(self)
    self.total = None
    self.config(borderwidth=2, relief=RIDGE)
    #self.label = Banner(self, "No Rings", columnspan=2)
    self.noRings = IntegerEntry(self, label="No Rings")
    self.noRings.bind("<FocusOut>", self.__calc)
    self.totfn = totfn
    return

  def getTotalNoRings(self):
    return self.total

class CashRegister(Frame):
  def __init__(self, totfn=None):
    Frame.__init__(self)
    self.config(borderwidth=2, relief=RIDGE)
    self.label = Banner(self, "Cash Register", columnspan=2)
    
class TicketDetail(Frame):

  def __labelLine(self):
    line = dict()
    line["collected"] = ColumnLabel(self, "Tickets")
    line["desc"] = ColumnLabel(self, "Rate Description")
    line["rate"] = ColumnLabel(self, "Rate in $")
    line["extended"] = ColumnLabel(self, "Extended")
    nextRow(self)
    return line

  def __calcTotals(self, event=None):
    dollars = 0
    tickets = 0
    for key in self.ticketLines:
      line = self.ticketLines[key]
      extended = line["extended"].getfloat()
      if extended: dollars += extended
      count = line["collected"].getint()
      if count: tickets += count
    self.totalDollars["total"].setfloat(dollars)
    self.totalTickets["total"].setint(tickets)
    #self.totalDollars["collected"].setint(tickets)
    if self.totfn: self.totfn()
    
  def __ticketCalc(self, event):
    widget = event.widget
    value = widget.getint()
    rate = widget.rate
    if value == None or rate == 0: extended = None
    else: extended = value * widget.rate
    widget.ext.setfloat(extended)
 
  def __ticketLine(self, desc, rate=0, editCol=True, editExt=False):
    line = dict()
    line["collected"] = IntegerEntry(self, readonly=not editCol)
    #line["code"] = TextDisplay(self. code)
    line["desc"] = TextDisplay(self, desc)
    line["rate"] = FloatEntry(self, rate, readonly=True)
    line["extended"] = FloatEntry(self, readonly=not editExt)
    nextRow(self)    
    line["collected"].rate = rate
    line["collected"].ext = line["extended"]
    if editExt:
      line["extended"].bind("<FocusOut>", self.__calcTotals, add="+")
    else:
      line["collected"].bind("<FocusOut>", self.__ticketCalc, add="+")
    if editCol:
      line["collected"].bind("<FocusOut>", self.__calcTotals, add="+")
    return line

  def __ticketLineDict(self):
    lines = dict()
    lines['0:30'] = self.__ticketLine("Daily 00:30", 1.00)
    lines['1:00'] = self.__ticketLine("Daily 01:00", 2.00)
    lines['1:30'] = self.__ticketLine("Daily 01:30", 3.00)
    lines['2:00'] = self.__ticketLine("Daily 02:00", 4.00)
    lines['2:30'] = self.__ticketLine("Daily 02:30", 5.00)
    lines['Spec'] = self.__ticketLine("Special Event", 2.00)
    lines['OTIM'] = self.__ticketLine("Val Overtime")
    lines['PDAY'] = self.__ticketLine("Prior Day", editExt=True )
    lines['LOST'] = self.__ticketLine("Lost Ticket", 6.00)
    lines['VOID'] = self.__ticketLine("Voids")
    lines['DMAX'] = self.__ticketLine("Daily Max", 6.00)
    lines['FLAT'] = self.__ticketLine("Flat Rate", 2.00)
    lines['PPAY'] = self.__ticketLine("Promise to Pay", editExt=True)
    #lines['NTWE'] = self.__ticketLine("Night/Weekend", 1.50)
    lines['FVAL'] = self.__ticketLine("Fully Validated Tixs", editExt=True)
    lines['OVSH'] = self.__ticketLine("Over/Short", editCol=False, editExt=True)
    lines['MBIL'] = self.__ticketLine("Monthly Billing")
    #lines['NBIL'] = self.__ticketLine("Nightly Billing")
    return lines

  def __endingTickets(self, include=True):
    check = self.checkLine['check']
    self.plusMinus = 5 if check.checked() else 0
    voids = self.ticketLines['VOID']["collected"]
    voids.setPlusMinus(self.plusMinus)
    self.__calcTotals()
    return
    
  def __checkLine(self):
    self.endingTickets = IntVar()
    line = dict()
    line['tickets'] = IntegerEntry(self, readonly=True)
    line['check'] = Checkbox(self)
    line['check'].grid(row=self.currentRow, column=nextColumn(self), sticky=E)
    line['check'].config(command=self.__endingTickets)
    line['desc'] = Label(self, text="Include Ending Tickets")
    line['desc'].grid(row=self.currentRow, column=nextColumn(self), sticky=E+W)
    line['dollars'] = FloatEntry(self, readonly=True)
    nextRow(self)
    return line

  def __totalLine(self, label):
    line = dict()
    line["collected"] = IntegerEntry(self, "", readonly=True)
    line["desc"] = TextDisplay(self, label, justify=RIGHT, columnspan=2)
    line["total"] = FloatEntry(self, readonly=True)
    nextRow(self)
    return line

  def __init__(self, totfn=None):
    Frame.__init__(self)
    self.config(borderwidth=2, relief=RIDGE)
    self.label = Banner(self, "Collected Ticket Detail", columnspan=4)
    self.labelLine = self.__labelLine()
    self.ticketLines = self.__ticketLineDict()
    self.totalDollars = self.__totalLine("Total Dollars Collected")
    self.totalTickets = self.__totalLine("Total Tickets Collected")
    self.checkLine = self.__checkLine()
    self.plusMinus = 0
    self.totfn = totfn
    
  def getTotalDollars(self):
    total = self.totalDollars["total"].getfloat()
    return total

  def getTotalTickets(self):
    total = self.totalTickets["total"].getint()
    #total = self.totalDollars["collected"].getint()
    return None if total==None else total - self.plusMinus

  def setCheckDollars(self, f):
    self.checkLine['dollars'].setfloat(f, fmt="{:+0.2f}")
    return

  def setCheckTickets(self, i):
    self.checkLine['tickets'].setint(i, fmt="{:+0d}")
    return

class ShiftReport(Tk):

  def __checkTotals(self):
    totDollars = self.ticketDetail.getTotalDollars()
    totTickets = self.ticketDetail.getTotalTickets()
    drpDollars = self.cashDrop.getTotalDollars()
    trzTickets = self.ticketCount.getTotalTickets()
    totNoRings = self.noRings.getTotalNoRings()
    if totDollars and drpDollars:
      varDollars = drpDollars - totDollars
    else:
      varDollars = None
    if totTickets and trzTickets:
      varTickets = totTickets - trzTickets
      if totNoRings: varTickets -= totNoRings
    else:
      varTickets = None
    self.ticketDetail.setCheckDollars(varDollars)
    self.ticketDetail.setCheckTickets(varTickets)
    return

  def __init__(self):
    Tk.__init__(self)
    self.title("report")
    self.banner = Label(self, text="Cascade Garage Shift Report")
    self.banner.grid(row=0, column=0, columnspan=3)
    self.displayDate = DisplayDate(self)
    self.displayDate.grid(row=1, column=0, sticky=N)
    self.dateSpacer = Spacer()
    self.dateSpacer.grid(row=2, column=0, sticky=N)    
    self.cashDrop = CashDrop(self.__checkTotals)
    self.cashDrop.grid(row=3, column=0, sticky=N)
    self.cashSpacer = Spacer()
    self.cashSpacer.grid(row=4, column=0, sticky=N)
    self.ticketCount = TicketCount(self.__checkTotals)
    self.ticketCount.grid(row=5, column=0, sticky=N)
    self.countSpacer = Spacer()
    self.countSpacer.grid(row=6, column=0, sticky=N)
    self.noRings = NoRings(self.__checkTotals)
    self.noRings.grid(row=7, column=0, sticky=N)
    self.ringSpacer = Spacer()
    self.ringSpacer.grid(row=8, column=0, sticky=N)
    self.rowconfigure(7, weight=1)
    self.detailSpacer = Spacer()
    self.detailSpacer.grid(row=1, column=1, rowspan=8)
    self.ticketDetail = TicketDetail(self.__checkTotals)
    self.ticketDetail.grid(row=1, column=2, rowspan=8)
    #after 7PM, assume second shift - add ending tickets
    if time.strftime('%H') > '19': 
      self.ticketDetail.checkLine['check'].invoke()
    self.cashDrop.coinAmount.focus()
    center(self)
    return
    
if __name__ == "__main__":
  report = ShiftReport()
  report.mainloop()

