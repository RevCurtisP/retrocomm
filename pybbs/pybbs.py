#!/usr/bin/python
'''Plain Text BBS'''

import ConfigParser
from datetime import datetime
import os
import re
import select
import socket
import SocketServer
import sqlite3
import string
import threading
import time

CONFIG_FILE = "pybbs.cfg"

DEFAULT_CONFIG = {
'IPADDR': "127.0.0.1",
'PORT': "2323", 
'TIMEOUT': "0",
'DEBUG': "4",
'LOGFILE': None,
'FILEDIR': None,
'DBNAME': "pybbs.db"
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

#Telnet Command Code Sequences
ECHO = '\x01' #      Echo Option
DONT = '\xFE' #      Don't Command
IAC  = '\xFF' #      Interpret as Command

#Character Sequence Constants
CLRSCRN = SPC + FF + BS
NEWLINE = CR + LF
ECHOOFF = IAC + DONT + ECHO

class Config(object):
  def __init__(self):
    object.__init__(self)
    self.config = ConfigParser.ConfigParser(DEFAULT_CONFIG)
    result = self.config.read(CONFIG_FILE)
    if result:
      print "Using config file", result
    else:
      print "Unable to read file", CONFIG_FILE
  def getstr(self, section, option):
    try: 
      result = self.config.get(section, option)
      print "Using config file section", section, "option", option
    except: 
      result = DEFAULT_CONFIG[option]
      print "Using default option", option
    return result
  def getint(self, section, option):
    try: 
      return int(self.getstr(section, option))
    except ValueError as err:
      print ValueError, "in section", section, "option", option
      quit()

class Database(object):
  def __debug(self, message, level=0):
    if self.debug: self.debug(message, level)
  def __init__(self, dbname, debug=None):
    self.debug = debug
    self.__debug('Opening Database ' + dbname)
    self.conn = sqlite3.connect(dbname)
    self.crsr = self.conn.cursor()
  def execute(self, query):
    self.__debug('Executing Query: ' + query, 6)
    self.crsr.execute(query)
    self.conn.commit()
  def create_table(self, table, columns):
    self.__debug('Creating Database Table ' + table, 4)
    query = 'CREATE TABLE IF NOT EXISTS ' + table + ' ( ' + columns +' )'
    self.execute(query)
  def read_rows(self, table, criteria):
    self.__debug('Reading Rows from Table ' + table, 4)
    self.__debug('With Criteria ' + str(criteria), 4)
    where = []
    what = []
    for column, value in criteria.items():
      where.append(column + '=?')
      what.append(value)
    query = 'SELECT * FROM ' + table + ' WHERE ' + ', '.join(where)
    columns = tuple(what)
    self.__debug('Query: ' + query, 4)
    self.__debug('Columns: ' + str(columns), 4)
    self.crsr.execute(query, columns)
    return self.crsr.fetchall()
  def write_row(self, table, columns):
    self.__debug('Writing Row to Table ' + table, 4)
    query = 'INSERT INTO ' + table + ' VALUES(?,?,?,?,?)'
    self.__debug('Query: ' + query)
    self.__debug('Columns: ' + str(columns))
    self.crsr.execute(query, columns)
    self.conn.commit()    

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
  def __debug(self, message, level=0):
    if level <= self.debuglevel:
      decoded = message.encode('string_escape')
      print self.threadid, decoded
  def __config(self):
    config = Config()
    self.config = config
    self.debuglevel = config.getint('BBS', 'DEBUG')
    self.timeout = config.getint('BBS', 'TIMEOUT')
    self.filedir = config.getstr('BBS', 'FILEDIR')
    self.dbname = config.getstr('BBS', 'DBNAME')
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
    self.__debug("BBS Initialized", 1)
    self.__clearInBuffer()
  def recv(self):
    data = self.socket.recv(32)
    if data: self.__debug("recv>"+data, 9)
    return data
  def send(self, data):
    self.socket.send(data)
    self.__debug("send>"+data, 9)
  def write(self, data=None):
    if data:
       self.__debug("write>"+data, 8)
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
  def fillbuffer(self):
    data = self.recv()
    if data:
      self.inbuffer += data
      if self.echo: self.send(data)
  def readLine(self, prompt=None):
    if prompt: self.writePrompt(prompt)
    while True:
      cr = self.inbuffer.find(CR)
      lf = self.inbuffer.find(LF)
      if cr > -1 or lf > -1: break
      self.fillbuffer()
    if cr < 0:   #only an LF was received
      i = lf; j = lf + 1; nl = CR
    elif lf < 0: #only a CR was recieved
      i = cr; j = cr + 1; nl = LF
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
    self.__debug("read>"+line+nl, 8)
    if nl == LF: self.write(CR+LF)
    return line
  def readCommand(self, prompt='Command>'):
    command = self.readLine(prompt).strip().upper()
    self.__debug("Received command "+command, 2)
    return command
  def readBlock(self, desc='Text'):
    block = []
    self.writeLine('Enter ' + desc + ' below')
    self.writeLine('Single . on a line to exit')
    while True:
      line = self.readLine()
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
    self.__debug("Authenticating", 2)
    self.username = None
    while not self.username:
      username = self.readLine("User Name:",).strip()
      self.__debug("Received User Name '"+username+"'", 3)
      if re.match('^[A-Z|a-z][A-Z|a-z|0-9]*$', username):
        self.username = username
      else:
        time.sleep(.5)
        self.writeLine("Invalid User Name")
    self.__debug("Logged in as "+self.username, 2)
    self.log.write('User ' + self.username + ' logged in')
  def info(self):
    self.writeLine("Enter ? for Help")
  def main(self):
    self.menu = self.main_menu
    while True:
      command = self.readCommand()
      if command == 'QUIT' or command == 'Q':
        self.writeLine(QUITMSG)
        self.writeLine(LOGOUT)
        self.log.write('User ' + self.username + ' logged out')
        break
      else:
        self.menu(command)
  def main_menu(self, command):
      if command == 'HELP' or command == '?':
        self.writeLine('HELP Display this text')
        if self.filedir: self.writeLine('FILE Enter File Library')
        self.writeLine('MAIL Electronic Mail')
        self.writeLine('USER Display user info')
        self.writeLine('QUIT Log out of BBS')        
      elif command == 'USER' or command == 'U':
        self.writeLine('User Name: '+self.username)
        self.writeLine('IP Address: '+self.user_ip)
        self.writeLine('Online for '+str(self.elapsed())+' seconds')
      elif command == 'FILE' or command == 'F':
        if self.filedir:
          self.writeLine('Entering File Library')        
          self.menu = self.file_menu
        else: self.writeLine('File Library Not Available')
      elif command == 'MAIL' or command == 'M':
          self.writeLine('Electronic Mail Menu')        
          self.menu = self.mail_menu
      else:
        self.writeLine('Invalid command.')
  def file_menu(self, command):
      if command == 'HELP' or command == '?':
        self.writeLine('HELP Display this text')
        self.writeLine('LIST Display File List')
        self.writeLine('READ Read File Contents')
        self.writeLine('EXIT Return to Main Menu')
      elif command == 'LIST' or command == 'L':
        files = os.listdir(self.filedir)
        if len(files):
          self.writeLine('File           Date   Size')
          for file in files:
            spec = os.path.join(self.filedir, file)
            stat = os.stat(spec)
            date = datetime.fromtimestamp(stat.st_ctime).strftime(' %m/%d/%y ')
            size = str(stat.st_size)
            line = file.ljust(12) + date + size
            self.writeLine(line)
        else:
          self.writeLine('No Files in Library')
      elif command == 'READ' or command == 'R':
        name = self.readCommand("File Name?")
        spec = os.path.join(self.filedir, name)
        try:
          with open(spec) as file:
            for line in file:
              self.writeLine(line.strip())
        except IOError as err:
          self.writeLine("Error Opening File " + name)
      elif command == 'EXIT' or command == 'X':
        self.writeLine('Exiting File Library')        
        self.menu = self.main_menu
      else:
        self.writeLine('Invalid command.')
  def mail_menu(self, command):
      if command == 'HELP' or command == '?':
        self.writeLine('HELP Display this text')
        self.writeLine('LIST Display Message List')
        self.writeLine('READ Read Email Message')
        self.writeLine('SEND Send Email Messages')
        self.writeLine('EXIT Return to Main Menu')
      elif command == 'LIST' or command == 'L':
        criteria = {'RECIPIENT': self.username}
        rows = self.db.read_rows('EMAIL', criteria)
        for row in rows:
          (sender, recipient, timestamp, subject, message) = row 
          date_time = datetime.fromtimestamp(timestamp).strftime('%m/%d/%y %H:%M')
          self.writeLine(date_time + ' ' + sender + ' - ' + subject)
      elif command == 'READ' or command == 'R':
        criteria = {'RECIPIENT': self.username}
        rows = self.db.read_rows('EMAIL', criteria)
        for row in rows:
          (sender, recipient, timestamp, subject, message) = row 
          date = datetime.fromtimestamp(timestamp).strftime('%m/%d/%y %H:%M')
          block = message.split('\n')
          self.writeLine('From: ' + sender)
          self.writeLine('Date: ' + date)
          self.writeLine('Subject: ' + subject)
          self.writeBlock(block)
          self.readLine('...Enter to Continue...')
      elif command == 'SEND' or command == 'S':
        sender = self.username
        recipient = self.readLine('To User:')
        if not recipient: return
        subject = self.readLine('Subject')
        if not subject: return
        block = self.readBlock('Message')
        message = '\n'.join(block)
        timestamp = time.mktime(time.localtime())
        columns = (sender, recipient, timestamp, subject, message)
        self.db.write_row('EMAIL', columns)
      elif command == 'EXIT' or command == 'X':
        self.writeLine('Returning to Main Menu')        
        self.menu = self.main_menu
      else:
        self.writeLine('Invalid command.')
  def open_db(self):
    self.db = Database(self.dbname, self.__debug)
    self.db.create_table('EMAIL', 'SENDER TEXT, RECIPIENT TEXT, DATETIME REAL, SUBJECT TEXT, MESSAGE')
  def start(self):
    self.log = Log(self.threadid)
    self.log.open(self.config.getstr('BBS', 'LOGFILE'))
    self.log.write('Connection from ' + self.user_ip + ' on Port ' + str(self.user_port))
    self.__debug("BBS Started", 1)
    self.time_login = time.time()
    self.enabletimeout()
    self.open_db()
    try:
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
    except KeyboardInterrupt:
      print "\nCaught Keyboard Interrupt"
    self.__debug("BBS Exited", 1)

class BBS_Handler(SocketServer.BaseRequestHandler):
  def handle(self):
    socket = self.request
    bbs = BBS(socket)
    bbs.start()
      
class BBS_Server(SocketServer.TCPServer):
  allow_reuse_address = True

if __name__ == "__main__":
  config = Config()
  ipaddr = config.getstr('SERVER', 'IPADDR')
  port = config.getint('SERVER', 'PORT')
  log = Log()
  log.open(config.getstr('SERVER', 'LOGFILE'))
  server = BBS_Server((ipaddr, port), BBS_Handler)
  ipaddr, port = server.server_address
  log.write('Server Opened on ' + ipaddr + ' Port ' + str(port))
  print "Listening on {0:} port {1:}".format(ipaddr, port)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    print "\nCaught Keyboard Interrupt"
    log.write('Server terminated by keyboard interrupt')
  print 'Exiting Server'
  quit()

