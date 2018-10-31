#!/usr/bin/python
'''Plain Text BBS'''

import ConfigParser
import re
import select
import socket
import SocketServer
import string
import threading
import time

DEBUG = 8

CONFIG_FILE = "pybbs.cfg"

DEFAULT_CONFIG = {
'IPADDR': "127.0.0.1",
'PORT': "2323", 
'TIMEOUT': "0",
'DEBUG': "8"
}

#Constants
BBSNAME = "RetroBBS"
WELCOME = "Welcome to " + BBSNAME
PROMPT = ">"
QUITMSG = "Thank you for calling " + BBSNAME
LOGOUT = "Logging Out"

#Character Constants
NUL = '\x00'  # ^@ - Null
BRK = '\x03'  # ^C - Break
BEL = '\x07'  # ^G - Bell
BS  = '\x08'  # ^H - Backspace
LF  = '\x0A'  # ^J - Line Feed
VT  = '\x0B'  # ^K - Vertical Tab
FF  = '\x0C'  # ^L - Form Feed
CR  = '\x0D'  # ^M - Carriage Return
ESC = '\x1B'  # ^[ - Escape
SPC = ' '     #    - Space
DEL = '\x7F'  #      Delete
CLRSCRN = SPC + FF + BS
NEWLINE = CR + LF

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
    print self.config
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

class BBS(object):
  def __clearInBuffer(self):
    self.inbuffer = ""
  def __debug(self, message, level=0):
    if level <= self.debuglevel:
      decoded = message.encode('string_escape')
      print self.threadid, decoded
  def __getthreadid(self):
    thread = threading.current_thread()
    threadid = thread.ident
    if threadid < 0: threadid += 4294967296
    return threadid
  def __config(self):
    config = Config()
    self.config = config
    self.debuglevel = config.getint('BBS', 'DEBUG')
    self.timeout = config.getint('BBS', 'TIMEOUT')
  def __init__(self, socket):
    self.socket = socket
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
    return line
  def readCommand(self, prompt='Command'):
    command = self.readLine(prompt+">").strip().upper()
    self.__debug("Received command "+command, 2)
    return command
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
  def info(self):
    self.writeLine("Enter ? for Help")
  def main(self):
    while True:
      command = self.readCommand()
      if command == 'HELP' or command == '?':
        self.writeLine('HELP Display this text')
        self.writeLine('USER Display user info')
        self.writeLine('QUIT Log out of BBS')        
      elif command == 'USER':
        self.writeLine('User Name: '+self.username)
        self.writeLine('Online for '+str(self.elapsed())+' seconds')
      elif command == 'QUIT':
        self.writeLine(QUITMSG)
        self.writeLine(LOGOUT)
        break
      else:
        self.writeLine('Invalid command.')
  def start(self):
    self.__debug("BBS Started", 1)
    self.time_login = time.time()
    self.enabletimeout()
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
  server = BBS_Server((ipaddr, port), BBS_Handler)
  ipaddr, port = server.server_address
  print "Listening on {0:} port {1:}".format(ipaddr, port)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    print "\nCaught Keyboard Interrupt"
  print 'Exiting Server'
  quit()

