#!/usr/bin/python2
'''Early 1980's Style Plain Text BBS'''

import ConfigParser
from datetime import datetime
import os
import re
import select
import socket
import SocketServer
import sqlite3
import string
import sys
import threading
import time

libdir = "lib"
phoon = "odphoon.py"
if os.path.exists(libdir):
  sys.path.append(libdir)
  if os.path.exists(os.path.join(libdir,phoon)):
    from odphoon import Odphoon
  else:
    phoon = None

weather = 'weather.py'
if os.path.exists(weather): from weather import Weather
else: weather = None

CONFIG_FILE = "pybbs.cfg"

'''Debug Levels
   1 - Default level
   2 - Show connects, logins, and disconnects
   3 - Show user actions and database queries
   4 - Show lines sent and received
   5 - Show all data sent and received'''

DEFAULT_CONFIG = {
'IPADDR': "127.0.0.1",
'PORT': "2323", 
'TIMEOUT': "0",
'DEBUG': "4",
'DEBUGFILE': "pybbs.dbg",
'LOGFILE': None,
'FILEDIR': None,
'DBNAME': "pybbs.db",
'CHAT': True
}

DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M:%S'

#Constants
BBSNAME = "RetroBBS"
WELCOME = "Welcome to " + BBSNAME
PROMPT = ">"
QUITMSG = "Thank you for calling " + BBSNAME
LOGOUT = "Logging Out"

#ASCII Control Code Constants
NUL  = '\x00' # ^@ - Null
BRK  = '\x03' # ^C - Break
BEL  = '\x07' # ^G - Bell
BS   = '\x08' # ^H - Backspace
HT   = '\x09' # ^I - Horizontal Tab
LF   = '\x0A' # ^J - Line Feed
VT   = '\x0B' # ^K - Vertical Tab
FF   = '\x0C' # ^L - Form Feed
CR   = '\x0D' # ^M - Carriage Return
ESC  = '\x1B' # ^[ - Escape
SPC  = ' '    #    - Space
DEL  = '\x7F' #      Delete

#Telnet Command Code Options
ECHO = '\x01' #Echo
SGO =  '\x03' #Suppress Go Ahead
STS =  '\x05' #Status
TTYP = '\x18' #Terminal Type
WSIZ = '\x1F' #Window Size
TSPD = '\x20' #Terminal Speed
RFC  = '\x21' #Remote Flow Control
LMOD = '\x22' #Line Mode
ENV  = '\x24' #Environment Variables
OPTS = {ECHO:"ECHO",SGO:"SUPPRESS_GO_AHEAD",STS:"STATUS",TTYP:"TERMINAL_TYPE",
        WSIZ:"WINDOW_SIZE",TSPD:"TERMINAL_SPEED",RFC:"REMOTE_FLOW_CONTROL",
        LMOD:"LINE_MODE",ENV:"ENVIRONMENT_VARIABLES"}

#Telnet Command Code Sequences
AYT  = '\xF6' #Are You There?
WILL = '\xFB' #Don't Command
WONT = '\xFC' #Won't Command
DO   = '\xFD' #Do Command
DONT = '\xFE' #Don't Command

IAC  = '\xFF' #Interpret as Command
CMDS = {AYT:"AYT",WILL:"WILL",WONT:"WONT",DO:"DO",DONT:"DONT"}

#ANSI Escape Sequences
DELETE = ESC + '[3~'

#Character Sequence Constants
BACKSPC = BS + SPC + BS
CLRSCRN = SPC + FF + BS
NEWLINE = CR + LF
ECHOOFF = IAC + DONT + ECHO

class Config(object):
  def __debug(self, message):
    if self.verbose:
      sys.stdout.write(message + '\n')
  def __init__(self, verbose=False):
    self.verbose = verbose
    self.config = ConfigParser.ConfigParser(DEFAULT_CONFIG)
    result = self.config.read(CONFIG_FILE)
    if result:
      self.__debug("Using config file " + str(result))
    else:
      self.__debug("Unable to read file " + CONFIG_FILE)
  def getstr(self, section, option):
    try: 
      result = self.config.get(section, option)
      self.__debug("Using config file section " + section + " option " + option)
    except: 
      result = DEFAULT_CONFIG[option]
      self.__debug("Using default option " + option)
    return result
  def getint(self, section, option):
    try: 
      return int(self.getstr(section, option))
    except ValueError as err:
      self.__debug(str(ValueError) + " in section " + section + " option " + option)
      quit()

class Debug(object):
  def __init__(self, level=0, debugfile=None, threadid=None):
    self.level = level
    if debugfile: self.file = open(debugfile, 'w')
    else: self.file = sys.stdout
    if not threadid:
      thread = threading.current_thread()
      threadid = thread.ident
    self.threadid = threadid
  def write(self, message, level=1):
    if level <= self.level:
      timestamp = datetime.now().strftime('%m/%d %H:%M')
      if type(message) == unicode: encoding = 'unicode_escape'
      elif type(message) == str: encoding = 'string_escape'
      else: encoding = None
      if encoding: message = message.encode(encoding, 'ignore')
      self.file.write(str(self.threadid) + ' ' + timestamp + ' ' + message + '\n')

class Database(object):
  def __debug(self, message, level=1):
    if self.debug: self.debug.write(message, level)
  def __init__(self, dbname, debug=None):
    self.debug = debug
    self.__debug('Opening Database ' + dbname)
    self.conn = sqlite3.connect(dbname)
    self.crsr = self.conn.cursor()
  def execute(self, query):
    self.__debug('Executing Query: ' + query, 4)
    self.crsr.execute(query)
    self.conn.commit()
  def create_table(self, table, columns):
    self.__debug('Creating Database Table ' + table, 3)
    query = 'CREATE TABLE IF NOT EXISTS ' + table + ' ( ' + columns +' )'
    self.execute(query)
  def count_rows(self, table, criteria):
    cols = []
    what = []
    for column, value in criteria.items():
      cols.append(column + '=?')
      what.append(value)
    where = ' AND '.join(cols)
    query = 'SELECT COUNT(*) FROM ' + table + ' WHERE ' + where
    col = tuple(what)
    self.crsr.execute(query, col)
    rows = self.crsr.fetchall()
    return rows[0][0]
  def last_row(self, table):
    query = 'SELECT MAX(ROWID) FROM ' + table 
    self.crsr.execute(query)
    rows = self.crsr.fetchall()
    return rows[0][0]
  def read_row(self, table, criteria):
    rows = self.read_rows(table, criteria, 1)
    return rows[0] if len(rows) else None
  def read_rows(self, table, criteria, limit=None):
    self.__debug('Reading Rows from Table ' + table, 3)
    self.__debug('With Criteria ' + str(criteria), 3)
    cols = []
    what = []
    for column, value in criteria.items():
      cols.append(column + '=?')
      what.append(value)
    where = ' AND '.join(cols)
    query = 'SELECT rowid,* FROM ' + table + ' WHERE ' + where
    if limit: query += ' LIMIT ' + str(limit)
    col = tuple(what)
    self.__debug('Query: ' + query, 3)
    self.__debug('Columns: ' + str(col), 3)
    self.crsr.execute(query, col)
    rows = self.crsr.fetchall()
    self.__debug('Read Rows ' + str(rows), 3)
    return rows
  def update_row(self, table, criteria, columns):
    self.__debug('Writing Row to Table ' + table, 3)
    what = []
    cols = []
    sets = []
    for column, value in columns.items():
      sets.append(column + '=?')
      what.append(value)
    set = ", ".join(sets)
    for column, value in criteria.items():
      cols.append(column + '=?')
      what.append(value)
    where = ' AND '.join(cols)
    col = tuple(what)
    query = 'UPDATE ' + table + ' SET ' + set + ' WHERE ' + where
    self.__debug('Query: ' + query, 3)
    self.__debug('Columns: ' + str(col), )
    self.crsr.execute(query, col)
    self.conn.commit()    
  def write_row(self, table, columns):
    self.__debug('Writing Row to Table ' + table, 3)
    qmarks = ['?'] * len(columns)
    subst = ",".join(qmarks)
    query = 'INSERT INTO ' + table + ' VALUES(' + subst + ')'
    self.__debug('Query: ' + query, 3)
    self.__debug('Columns: ' + str(columns), 3)
    self.crsr.execute(query, columns)
    self.conn.commit()

class FileList:
  def __init__(self, filedir, debug=None):
    self.debug = debug
    if self.debug: debug.write("Reading directory %s" % filedir, 3)
    self.filedir = filedir
    self.fileindex = 0
    self.files = os.listdir(self.filedir)
    if self.debug: debug.write("Found %d files" % len(self.files), 3)
  def __iter__(self):
    return self
  def __len__(self):
    return len(self.files)
  def next(self):
    if self.fileindex < len(self.files):
      file = self.files[self.fileindex]
      self.fileindex += 1
      spec = os.path.join(self.filedir, file)
      stat = os.stat(spec)
      date = datetime.fromtimestamp(stat.st_ctime).strftime(' %m/%d/%y ')
      size = str(stat.st_size)
      return file.ljust(12) + date + size
    else: 
      raise StopIteration

class Log(object):
  def __getthreadid(self):
    thread = threading.current_thread()
    threadid = thread.ident
    if threadid < 0: threadid += 4294967296
    return threadid
  def __init__(self, threadid = None):
    if threadid:
      self.threadid = threadid
    else:
      self.threadid = self.__getthreadid()
  def open(self, logname):
    self.logname = logname
    if self.logname: 
      self.logfile = open(self.logname, "a")
    else:
      self.logfile = None
  def write(self, entry):
    if self.logfile:
      logtime = datetime.now().strftime(DATE_FORMAT + ' ' + TIME_FORMAT)
      line = "{0:} {1:}: {2:}\n".format(logtime, self.threadid, entry)
      self.logfile.write(line)
      self.logfile.flush()

class BBS(object):
  def __clearInBuffer(self):
    self.inbuffer = ""
  def __debug(self, message, level=1):
    if self.debug:
      self.debug.write(message, level)
  def __config(self):
    config = Config()
    self.config = config
    self.debuglevel = config.getint('BBS', 'DEBUG')
    self.debugfile = config.getstr('BBS', 'DEBUGFILE')
    self.timeout = config.getint('BBS', 'TIMEOUT')
    self.filedir = config.getstr('BBS', 'FILEDIR')
    self.dbname = config.getstr('BBS', 'DBNAME')
    self.chat = config.getint('BBS', 'CHAT')
  def __addapps(self):
    self.apps = False
    if phoon:
      self.odphoon = Odphoon()
      self.apps = True
    else:
      self.odphoon = None
    if weather:
      self.weather = Weather()
      self.apps = True
    else:
      self.weather = None
  def __getthreadid(self):
    thread = threading.current_thread()
    threadid = thread.ident
    if threadid < 0: threadid += 4294967296
    return threadid
  def __init__(self, socket):
    self.socket = socket
    self.user_ip, self.user_port = self.socket.getpeername()
    self.echo = True
    self.threadid = self.__getthreadid()
    self.__config()
    self.debug = Debug(self.debuglevel, self.debugfile, self.threadid)
    self.__addapps() 
    self.__debug("BBS Initialized", 1)
    self.__clearInBuffer()
  def recv(self, timeout=False):
    try: 
      data = self.socket.recv(32)
    except socket.timeout as x:
      if timeout: return None
      else: raise EORError()
    if data: 
      self.__debug("recv>"+data, 5)
    else:
      raise EOFError()
    return data
  def send(self, data):
    if data == BS: data = BACKSPC
    self.socket.send(data)
    self.__debug("send>"+data, 5)
  def write(self, data=None):
    if data:
       self.__debug("write>"+data, 4)
       self.send(data)
  def writeClearScreen():
    self.write(FF+BS)
  def writeLine(self, data=""):
    self.write(data + NEWLINE)
  def writePrompt(self, data):
    self.write(NEWLINE + data + SPC)
  def writeBlock(self, block):
    self.writeLine()
    for line in block:
      self.writeLine(line)
  def fillbuffer(self, timeout=None):
    if timeout: 
      oldTimeout = self.socket.gettimeout()
      self.socket.settimeout(timeout)
    data = self.recv(timeout)
    if data:
      if data == ESC: data = BRK
      elif data in [DEL, DELETE]: data = BS
      if self.telnetClient: 
        data = self.checkTelnetCommands(data)
      self.inbuffer += data
      if self.echo: 
        if len(data)>1 or data>=' ' or data in [BS, CR, LF]: 
          self.send(data)
    if timeout: 
      self.socket.settimeout(oldTimeout)
  def sendTelnetCommand(self, command):
    self.send(IAC + command)
  def processTelnetCommand(self, command, option):
    if command in CMDS: cmd = CMDS[command]
    else: cmd = str(ord(command))
    txt = "Processing Telnet Command " + cmd
    if option != None: 
      if option in OPTS: opt = OPTS[option]
      else: opt = "with Option " + str(ord(option))
      txt += " " + opt
    self.__debug(txt, 4)
  def checkTelnetCommands(self, data):
    while True:
      i = data.find(IAC)
      if i > -1:
        j = i + 1
        command = data[j]
        if command in {DO, DONT, WILL, WONT}: 
          j = j + 1
          option = data[j]
        else: 
          option = None
        data = data[:i] + data[j+1:]
        self.__debug("data=" + data, 5)
        self.processTelnetCommand(command, option)
      else:
        break  
    return data
  def readLine(self, prompt=None, timeout=None):
    if prompt: self.writePrompt(prompt)
    while True:
      brk = self.inbuffer.find(BRK)
      cr = self.inbuffer.find(CR)
      lf = self.inbuffer.find(LF)
      if brk > -1 or cr > -1 or lf > -1: break
      bufferlen = len(self.inbuffer)
      self.fillbuffer(timeout)
      if timeout and len(self.inbuffer) == bufferlen: return None
    if brk > -1: #Ctrl-C was received
      i = brk;  j = brk + 1; nl = BRK
    elif cr < 0:   #only an LF was received
      i = lf; j = lf + 1; nl = LF
    elif lf < 0: #only a CR was recieved
      i = cr; j = cr + 1; nl = CR
    else:        #both a CR and LF were received
      if lf < cr:         #LF is first
        i = lf; j = lf + 1; nl = LF
      elif lf == cr + 1:  #CR+LF
        i = cr; j = lf + 1; nl = CR+LF
      else:               #CR is first
        i = cr; j = cr + 1; nl = CR
    line = self.inbuffer[:i]
    self.inbuffer = self.inbuffer[j:]
    while True: #scan for BackSpace
      bs = line.find(BS)
      if bs < 0: break                            
      elif bs: line = line[:bs-1] + line[bs+1:]
      else: line = line[1:]
    self.__debug("read>"+line+nl, 4)
    if nl == CR: self.write(LF) #Write LF if only CR received
    if nl == BRK: return BRK
    else: return line
  def readCommand(self, prompt='Command>'):
    command = self.readLine(prompt).strip().upper()
    self.__debug("Received command "+command, 3)
    return command
  def readBlock(self, desc='Text'):
    block = []
    self.writeLine('Enter ' + desc + ' below')
    self.writeLine('Single . on a line to exit')
    while True:
      line = self.readLine()
      if line == BRK: return BRK
      if line.strip() == '.': return block
      block.append(line)
  def elapsed(self, format=None):
    '''Returns time elapsed since start()'''
    _elapsed = int(time.time() - self.time_login)
    return _elapsed
  def enabletimeout(self):
    if self.timeout: self.socket.settimeout(self.timeout)
  def welcome(self):
    self.writeLine(CLRSCRN + WELCOME)
  def login(self):
    self.__debug("Authenticating", 3)
    self.username = None
    while not self.username:
      username = self.readLine("User Name:",).strip()
      self.__debug("Received User Name '"+username+"'", 3)
      if re.match('^[A-Z|a-z][A-Z|a-z|0-9]*$', username):
        self.username = username
      else:
        time.sleep(.5)
        self.writeLine('Invalid User Name')
    self.__debug("Logged in as "+self.username, 2)
    self.log.write('User ' + self.username + ' logged in')
    now = time.mktime(time.localtime())
    row = self.db.read_row('USERS', {'USERID': self.username})
    if row:
      (rowid, userid, password, role, timestamp, msgno) = row
      if msgno: self.msgno = msgno
      date_time = datetime.fromtimestamp(timestamp).strftime('%m/%d/%y %H:%M')
      self.writeLine('Last login ' + date_time)
      self.db.update_row('USERS', {'USERID': self.username}, {'UNIXTIME': now})
    else:
      self.password = ''
      columns = (self.username, self.password, 'USER', now, self.msgno)
      self.db.write_row('USERS', columns)
    msgCount = max(self.lastMsgNo() + 1 - self.msgno, 0)
    if msgCount:
      self.writeLine('There are %i unread post(s).' % msgCount)
    mailCount = self.db.count_rows('EMAIL', {'RECIPIENT': self.username, 'READ': 0})
    if mailCount:
      self.writeLine('You have %i new email(s).' % mailCount)
  def info(self):
    self.writeLine("Enter ? for Help")
  def lastMsgNo(self):
    rowid = self.db.last_row('FORUM')
    try:
      msgno = int(rowid)
    except (TypeError, ValueError) as x:
      msgno = 0
    return msgno
  def chatroom(self):
    address = ('localhost', 9999)
    skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    skt.settimeout(.1)
    try:
      skt.connect(address)
      skt.sendall(self.username)
    except Exception as x:
      self.__debug("Error " + str(x) + " connecting to chat server ", 2)
    newline = None
    while True:
      self.fillbuffer(.1)
      try:
        if len(self.inbuffer):
          line = self.readLine(timeout=5)
          if line: 
            skt.sendall(line)
            newline = None
          else: 
            if newline == None: newline = True
        line = skt.recv(1024)
        self.__debug("SKT.RECV>" + line, 4)
        if line:
          if str(line).find("[%s] " % self.username):
            if newline:
              self.writeLine('')
              newline = False
            self.writeLine(line)
        else:
          self.__debug("Exiting chatroom", 3)        
          break
      except socket.timeout as x:
        continue
      except Exception as x:
        self.__debug("Error %s communicating with chat server" % s, 2)
    skt.close()
  def main(self):
    self.menu = self.main_menu
    while True:
      command = self.readCommand()
      if command == BRK: continue
      if command == 'QUIT' or command == 'Q':
        self.writeLine(QUITMSG)
        self.writeLine(LOGOUT)
        self.log.write('User ' + self.username + ' logged out')
        break
      else:
        self.menu(command)
  def main_menu(self, command):
    if command == '?':
      line = '[H]ELP, [L]IST, [R]EAD, [N]EXT, [P]OST, '
      if self.apps: line += '[A]PPS, '
      if self.chat: line += '[C]HAT, '
      if self.filedir: line += '[F]ILE, '
      line += '[M]AIL, [U]SER, [Q]UIT'
      self.writeLine(line)
    elif command == 'HELP' or command == 'H':
      self.writeLine('HELP Display this text')
      self.writeLine('LIST Forum Message List')
      self.writeLine('READ Read Forum Message')
      self.writeLine('NEXT Read Next Message')
      self.writeLine('POST Post Forum Message')
      if self.apps: self.writeLine('APPS Applications Menu')
      if self.chat: self.writeLine('CHAT Enter Chat Room')
      if self.filedir: self.writeLine('FILE File Library Menu')
      self.writeLine('MAIL Electronic Mail Menu')
      self.writeLine('USER Display user info')
      self.writeLine('QUIT Log out of BBS')
    elif command == 'USER' or command == 'U':
      self.writeLine('User Name: '+self.username)
      self.writeLine('IP Address: '+self.user_ip)
      self.writeLine('Online for '+str(self.elapsed())+' seconds')
    elif command == 'APPS' or command == 'A':
      if self.apps:
        self.writeLine('Entering Applications Menu')        
        self.menu = self.apps_menu
      else: self.writeLine('Applications Not Available')        
    elif command == 'CHAT' or command == 'C':
      self.chatroom()
    elif command == 'FILE' or command == 'F':
      if self.filedir:
        self.writeLine('Entering File Library')        
        self.menu = self.file_menu
      else: self.writeLine('File Library Not Available')
    elif command == 'MAIL' or command == 'M':
        self.writeLine('Electronic Mail Menu')        
        self.menu = self.mail_menu
    elif command == 'LIST' or command == 'L':
      criteria = {'SUBFORUM': self.subforum}
      rows = self.db.read_rows('FORUM', criteria)
      for row in rows:
        (rowid, subforum, userid, timestamp, subject, message) = row
        msgno = str(rowid)
        date_time = datetime.fromtimestamp(timestamp).strftime('%m/%d/%y %H:%M')
        self.writeLine(msgno + ' - ' + userid + ' - ' + subject)
    elif command == 'POST' or command == 'P':
      subforum = 0
      userid = self.username
      subject = self.readLine('Subject:')
      if not subject: return
      block = self.readBlock('Message')
      message = '\n'.join(block)
      timestamp = time.mktime(time.localtime())
      columns = (subforum, userid, timestamp, subject, message)
      self.db.write_row('FORUM', columns)
    elif command in {'READ', 'R', 'NEXT', 'N'}:
      if command == 'READ' or command == 'R':
        while True:
          try:
            line = self.readLine('Message#:')
            if line == BRK: return
            self.msgno = int(line)
            break
          except ValueError as x:
            self.writeLine('Invalid entry')
      else:
        if self.msgno > self.lastMsgNo():
          self.writeLine('There are no new posts.')
          return          
        self.writeLine('Message#: ' + str(self.msgno))
      criteria = {'SUBFORUM': self.subforum, 'ROWID': self.msgno}
      row = self.db.read_row('FORUM', criteria)
      if row:
        (rowid, subforum, userid, timestamp, subject, message) = row
        date_time = datetime.fromtimestamp(timestamp).strftime('%m/%d/%y %H:%M')
        block = message.split('\n')
        self.writeLine('User: ' + userid)
        self.writeLine('Date: ' + date_time)
        self.writeLine('Subject: ' + subject)
        self.writeBlock(block)
        self.msgno += 1
        self.db.update_row('USERS', {'USERID': self.username}, {'MSGNO': self.msgno})
      else:
        self.writeLine('Message Not Found')
    else:
      self.writeLine('Invalid command.')
  def apps_menu(self, command):
    if command == '?':
      line = '[H]ELP, '
      if self.odphoon: line += '[M]OON, '
      if self.weather: line += '[W]THR, '
      line += 'E[X]IT'
      self.writeLine(line)
    elif command == 'HELP' or command == 'H':
      self.writeLine('HELP Display this text')
      if self.odphoon: self.writeLine('MOON Current Moon Phase')
      if self.weather: self.writeLine('WTHR Weather Report')
      self.writeLine('EXIT Return to Main Menu')
    elif command == 'MOON' or command == 'M':
      self.writeBlock(self.odphoon.putmoon(numlines=6))
    elif command == 'WTHR' or command == 'W':
      location = self.readLine('Location:')
      if location:
        self.writeLine('Getting weather for ' + location)
        self.writeBlock(self.weather.current(location))
    elif command == 'EXIT' or command == 'X':
      self.writeLine('Exiting Applications Menu')        
      self.menu = self.main_menu
    else:
      self.writeLine('Invalid command.')
  def file_menu(self, command):
    if command == '?':
      self.writeLine('[H]ELP, [L]IST, [R]EAD, E[X]IT')
    elif command == 'HELP' or command == 'H':
      self.writeLine('HELP Display this text')
      self.writeLine('LIST Display File List')
      self.writeLine('READ Read File Contents')
      self.writeLine('EXIT Return to Main Menu')
    elif command == 'LIST' or command == 'L':
      list = FileList(self.filedir, self.debug)
      if self.debug: self.debug.write("Listing %d files" % len(list), 3)
      if len(list):
        self.writeLine('File           Date   Size')
        for line in list:
          self.writeLine(line)
      else:
        self.writeLine('No Files in Library')
    elif command == 'READ' or command == 'R':
      name = self.readCommand("File Name?")
      if name == BRK: return
      spec = os.path.join(self.filedir, name)
      try:
        with open(spec) as file:
          for line in file:
            self.writeLine(line.rstrip())
      except IOError as err:
        self.writeLine("Error Opening File " + name)
    elif command == 'EXIT' or command == 'X':
      self.writeLine('Exiting File Library')        
      self.menu = self.main_menu
    else:
      self.writeLine('Invalid command.')
  def mail_menu(self, command):
    if command == '?':
      self.writeLine('[H]ELP, [L]IST, [R]EAD, [S]END, E[X]IT')
    elif command == 'HELP' or command == 'H':
      self.writeLine('HELP Display this text')
      self.writeLine('LIST Display Message List')
      self.writeLine('READ Read Email Messages')
      self.writeLine('SEND Send Email Message')
      #self.writeLine('KILL Delete All Messages')
      self.writeLine('EXIT Return to Main Menu')
    elif command == 'KILL' or command == 'K':
      self.writeLine('KILL not implemented')
    elif command == 'LIST' or command == 'L':
      criteria = {'RECIPIENT': self.username}
      rows = self.db.read_rows('EMAIL', criteria)
      if len(rows):
        for row in rows:
          (rowid, sender, recipient, timestamp, read, subject, message) = row
          status = ' ' if read else '*'
          date_time = datetime.fromtimestamp(timestamp).strftime('%m/%d/%y %H:%M')
          self.writeLine(status + ' ' + date_time + ' ' + sender + ' - ' + subject)
      else:
        self.writeLine('No mail found')
    elif command == 'READ' or command == 'R':
      rows = self.db.read_rows('EMAIL', {'RECIPIENT': self.username, 'READ': 0})
      if len(rows) == 0:
        rows = self.db.read_rows('EMAIL', {'RECIPIENT': self.username})
      if len(rows):
        for row in rows:
          (rowid, sender, recipient, timestamp, read, subject, message) = row 
          date = datetime.fromtimestamp(timestamp).strftime('%m/%d/%y %H:%M')
          block = message.split('\n')
          self.writeLine('From: ' + sender)
          self.writeLine('Date: ' + date)
          self.writeLine('Subject: ' + subject)
          self.writeBlock(block)
          line = self.readLine('...Enter to Continue...')
          if line == BRK: break
          self.db.update_row('EMAIL', {'ROWID': rowid}, {'READ': 1})
      else:
        self.writeLine('No mail found')
    elif command == 'SEND' or command == 'S':
      sender = self.username
      recipient = self.readLine('To User:')
      if not recipient or recipient == BRK: return
      subject = self.readLine('Subject:')
      if not subject or subject == BRK: return
      block = self.readBlock('Message')
      if block == BRK: return 
      message = '\n'.join(block)
      timestamp = time.mktime(time.localtime())
      read = 0
      columns = (sender, recipient, timestamp, read, subject, message)
      self.db.write_row('EMAIL', columns)
    elif command == 'EXIT' or command == 'X':
      self.writeLine('Returning to Main Menu')        
      self.menu = self.main_menu
    else:
      self.writeLine('Invalid command.')
  def open_db(self):
    self.db = Database(self.dbname, self.debug)
    self.db.create_table('EMAIL', 'SENDER TEXT, RECIPIENT TEXT, UNIXTIME REAL, READ INTEGER, SUBJECT TEXT, MESSAGE')
    self.db.create_table('FORUM', 'SUBFORUM INTEGER, USERID TEXT, UNIXTIME REAL, SUBJECT TEXT, MESSAGE')
    self.db.create_table('USERS', 'USERID TEXT, PASSWORD TEXT, ROLE TEXT, UNIXTIME REAL, MSGNO INTEGER')
  def start(self):
    self.log = Log(self.threadid)
    self.log.open(self.config.getstr('BBS', 'LOGFILE'))
    self.log.write('Connection from ' + self.user_ip + ' on Port ' + str(self.user_port))
    self.__debug("BBS Started", 1)
    self.telnetClient = True
    self.msgno = 1
    self.subforum = 0
    self.time_login = time.time()
    self.enabletimeout()
    self.open_db()
    try:
      #self.checkClient()
      self.welcome()
      self.login()
      self.info()
      self.main()
    except socket.timeout as err:
      self.writeLine()
      self.writeLine("No activity for "+str(self.timeout)+" minutes")
      self.writeLine(LOGOUT)
    except socket.error as err:
      errno, errmsg = err
      message = "Socket Error {0:} - {1:}".format(errno, errmsg)
      self.__debug(message, 1)
    except EOFError as err:
      self.__debug("Socket closed", 1)
      self.log.write("Socket closed")
    except KeyboardInterrupt:
      self.__debug("\nCaught Keyboard Interrupt", 1)
    self.__debug("BBS Exited", 1)
    self.log.write("BBS Exited")

class BBS_Handler(SocketServer.BaseRequestHandler):
  def handle(self):
    socket = self.request
    bbs = BBS(socket)
    bbs.start()

class BBS_Server(SocketServer.ThreadingTCPServer):
  allow_reuse_address = True

class ChatServer(object):
  clients = {}
  addresses = {}
  names = {}
  HOST = 'localhost'
  PORT = 9999
  BUFSIZ = 1024
  MAX_CLIENTS = 5
  def __debug(self, message, level=1):
    if self.debug:
      self.debug.write(message, level)
  def __config(self):
    config = Config()
    self.config = config
    self.debuglevel = config.getint('CHAT', 'DEBUG')
    self.debugfile = config.getstr('CHAT', 'DEBUGFILE')
  def __init__(self):
    self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.server.settimeout(1)
  def accept_incoming_connections(self):
    """Sets up handling for incoming clients."""
    while not self.stopped.is_set():
      try: 
        client, address = self.server.accept()
        host, port = address
        self.__debug("Client connected from " + host + " on Port " + str(port), 2)
        #client.send(bytes("NAME?"))
        self.addresses[client] = address
        threading.Thread(target=self.handle_client, args=(client,)).start()
      except socket.timeout as x:
        continue
      except Exception as x:
        self.__debug(str(x), 1)
    self.__debug('Exiting Chat Server', 1)
  def handle_client(self, client): 
    """Handles a single client connection."""
    client.settimeout(None)
    try:
      name = str(client.recv(self.BUFSIZ))
      self.__debug("Received name %s from client" % name, 3)
      self.names[client] = name
    except Exception as x:
      self.__debug("Error %s communicating with client" % x, 2)
      del self.clients[client]
      del self.addresses[client]
      return
    client.send(bytes("[Type .quit to exit chat]"))
    self.broadcast(bytes("[%s has joined the chat]" % name))
    self.clients[client] = name
    while True:
      try:
        msg = client.recv(self.BUFSIZ)
        self.__debug("CLIENT.RECV> %s" %msg, 4)
      except Exception as x:
        self.__debug("CLIENT.RECV> %s" % type(x), 4)
        self.__debug("CLIENT.RECV> %s" % x, 4)
        msg = None
      if msg:
        if msg[0] == bytes("."):
          cmd = str(msg[1:])
          self.__debug("Processing command %s" % cmd, 3)
          if cmd == "quit" or cmd == "q": break
          elif cmd == "who" or cmd == "w": 
            client.sendall("[%s]" % ", ".join(dict.values(self.names)))
          else: client.sendall("[Invalid command]")
        else:
          self.broadcast(msg, "[%s] " % name)
      else:
        break
    client.close()
    del self.clients[client]
    self.broadcast(bytes("[%s has left the chat]" % name))
    host, port = self.addresses[client]
    del self.addresses[client]
    self.__debug("Client disconnected from " + host + " on Port " + str(port), 2)
        
  def broadcast(self, msg, prefix=""):
    """Broadcasts a message to all the clients."""
    for sock in self.clients:
      sock.send(bytes(prefix) + msg)
    self.__debug("Broadcast: %s" % msg, 3)
  def start(self):
    self.threadid = threading.current_thread().ident
    self.__config()
    self.debug = Debug(self.debuglevel, self.debugfile, self.threadid)
    self.stopped = threading.Event()
    self.__debug("Starting Chat Server", 1)
    self.server.bind((self.HOST, self.PORT))
    self.__debug("Chat Server bound to " + self.HOST + " on Port " + str(self.PORT), 1)
    self.server.listen(self.MAX_CLIENTS)
    self.__debug("Waiting for connection...", 1)
    sys.stdout.write("Chat Server running on %s:%s\n" % (self.HOST, self.PORT))
    accept_thread = threading.Thread(target=self.accept_incoming_connections)
    accept_thread.start()  # Starts the infinite loop.
    accept_thread.join()
    self.server.close()
  def stop(self):
    self.__debug("Stopping Chat Server", 1)
    self.stopped.set()

if __name__ == "__main__":
  config = Config()
  debug = config.getstr('SERVER', 'DEBUG')
  ipaddr = config.getstr('SERVER', 'IPADDR')
  port = config.getint('SERVER', 'PORT')
  debuglevel = config.getint('SERVER', 'DEBUG')
  debugfile = config.getstr('SERVER', 'DEBUGFILE')
  debug = Debug(debuglevel, debugfile)
  log = Log()
  log.open(config.getstr('SERVER', 'LOGFILE'))
  if config.getint('CHAT', 'CHAT'):
    chatServer = ChatServer()
    threading.Thread(target=chatServer.start).start()
  else:
    chatServer = None
  server = BBS_Server((ipaddr, port), BBS_Handler)
  ipaddr, port = server.server_address
  log.write('Server Opened on ' + ipaddr + ' Port ' + str(port))
  debug.write("Listening on {0:} port {1:}".format(ipaddr, port), 1)
  sys.stdout.write("BBS Server running on %s:%s\n" % (ipaddr, port))
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    debug.write("Caught Keyboard Interrupt", 1)
    log.write('Server terminated by keyboard interrupt')
  if chatServer: chatServer.stop()
  debug.write('Exiting Server',1)
  sys.exit()
