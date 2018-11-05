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

#Telnet Command Code Sequences
ECHO = '\x01' #      Echo Option
DONT = '\xFE' #      Don't Command
IAC  = '\xFF' #      Interpret as Command

#Character Sequence Constants
CLRSCRN = SPC + FF + BS
NEWLINE = CR + LF
ECHOOFF = IAC + DONT + ECHO

class Config(object):
  def __debug(self, message):
    if self.verbose:
      print message
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
      self.__debug(str(ValueError) + " in section " + section + " option ", option)
      quit()

class Debug(object):
  def __init__(self, level=0, threadid=None):
    self.level = level
    if not threadid:
      thread = threading.current_thread()
      threadid = thread.ident
    self.threadid = threadid
  def write(self, message, level=1):
    if level <= self.level:
      if type(message) == unicode: encoding = 'unicode_escape'
      elif type(message) == string: encoding = 'string_escape'
      else: encoding = None
      if encoding:
        message = message.encode(encoding, 'ignore')
      print str(self.threadid) + ' ' + message

class Database(object):
  def __debug(self, message, level=1):
    if self.debug: self.debug.write(message, level)
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
  def read_row(self, table, criteria):
    rows = self.read_rows(table, criteria, 1)
    return rows[0] if len(rows) else None
  def read_rows(self, table, criteria, limit=None):
    self.__debug('Reading Rows from Table ' + table, 4)
    self.__debug('With Criteria ' + str(criteria), 4)
    where = []
    what = []
    for column, value in criteria.items():
      where.append(column + '=?')
      what.append(value)
    query = 'SELECT rowid,* FROM ' + table + ' WHERE ' + ' AND '.join(where)
    if limit: query += ' LIMIT ' + str(limit)
    columns = tuple(what)
    self.__debug('Query: ' + query, 4)
    self.__debug('Columns: ' + str(columns), 4)
    self.crsr.execute(query, columns)
    rows = self.crsr.fetchall()
    self.__debug('Read Rows ' + str(rows), 4)
    return rows
  def write_row(self, table, columns):
    self.__debug('Writing Row to Table ' + table, 4)
    qmarks = ['?'] * len(columns)
    subst = ",".join(qmarks)
    query = 'INSERT INTO ' + table + ' VALUES(' + subst + ')'
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
  def __debug(self, message, level=1):
    if self.debug:
      self.debug.write(message, level)
  def __config(self):
    config = Config()
    self.config = config
    self.debuglevel = config.getint('BBS', 'DEBUG')
    self.timeout = config.getint('BBS', 'TIMEOUT')
    self.filedir = config.getstr('BBS', 'FILEDIR')
    self.dbname = config.getstr('BBS', 'DBNAME')
    self.chat = config.getint('BBS', 'CHAT')
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
    self.debug = Debug(self.debuglevel, self.threadid)
    self.__debug("BBS Initialized", 1)
    self.__clearInBuffer()
  def recv(self, timeout=False):
    try: 
      data = self.socket.recv(32)
    except socket.timeout as x:
      if timeout: return None
      else: raise EORError()
    if data: 
      self.__debug("recv>"+data, 9)
    else:
      raise EOFError()
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
  def fillbuffer(self, timeout=None):
    if timeout: 
      oldTimeout = self.socket.gettimeout()
      self.socket.settimeout(timeout)
    data = self.recv(timeout)
    if data:
      self.inbuffer += data
      if self.echo: self.send(data)
    if timeout: 
      self.socket.settimeout(oldTimeout)
  def telnetCommands(self):
    return
  def readLine(self, prompt=None, timeout=None):
    if prompt: self.writePrompt(prompt)
    while True:
      self.telnetCommands()
      brk = self.inbuffer.find(BRK)
      cr = self.inbuffer.find(CR)
      lf = self.inbuffer.find(LF)
      if brk > -1 or cr > -1 or lf > -1: break
      bufferlen = len(self.inbuffer)
      self.fillbuffer(timeout)
      if timeout and len(self.inbuffer) == bufferlen: return None
    if cr < 0:   #only an LF was received
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
    self.__debug("read>"+line+nl, 8)
    if nl == CR: self.write(LF) #Write LF if only CR received
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
        self.writeLine('Invalid User Name')
    self.__debug("Logged in as "+self.username, 2)
    self.log.write('User ' + self.username + ' logged in')
  def info(self):
    self.writeLine("Enter ? for Help")
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
        if line:
          if str(line).find(self.username+":"):
            if newline:
              self.writeLine('')
              newline = False
            self.writeLine(line)
        else: break
      except socket.timeout as x:
        continue
      except Exception as x:
        self.__debug("Error " + str(x) + " communicating with chat server")
    skt.close()
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
      self.writeLine('LIST Forum Message List')
      self.writeLine('READ Read Forum Message')
      self.writeLine('NEXT Read Next Message')
      self.writeLine('POST Post Forum Message')
      if self.chat: self.writeLine('CHAT Enter Chat Room')
      if self.filedir: self.writeLine('FILE File Library Menu')
      self.writeLine('MAIL Electronic Mail Menu')
      self.writeLine('USER Display user info')
      self.writeLine('QUIT Log out of BBS')
    elif command == 'USER' or command == 'U':
      self.writeLine('User Name: '+self.username)
      self.writeLine('IP Address: '+self.user_ip)
      self.writeLine('Online for '+str(self.elapsed())+' seconds')
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
            self.msgno = int(self.readLine('Message#:'))
            break
          except ValueError as x:
            self.writeLine('Invalid entry')
      else:
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
      else:
        self.writeLine('Message Not Found')
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
            self.writeLine(line.rstrip())
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
      self.writeLine('KILL Delete All Messages')
      self.writeLine('EXIT Return to Main Menu')
    elif command == 'KILL' or command == 'K':
      self.writeLine('KILL not implemented')
    elif command == 'LIST' or command == 'L':
      criteria = {'RECIPIENT': self.username}
      rows = self.db.read_rows('EMAIL', criteria)
      for row in rows:
        (rowid, sender, recipient, timestamp, read, subject, message) = row 
        date_time = datetime.fromtimestamp(timestamp).strftime('%m/%d/%y %H:%M')
        self.writeLine(date_time + ' ' + sender + ' - ' + subject)
    elif command == 'READ' or command == 'R':
      criteria = {'RECIPIENT': self.username}
      rows = self.db.read_rows('EMAIL', criteria)
      for row in rows:
        (rowid, sender, recipient, timestamp, read, subject, message) = row 
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
      subject = self.readLine('Subject:')
      if not subject: return
      block = self.readBlock('Message')
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
  def start(self):
    self.log = Log(self.threadid)
    self.log.open(self.config.getstr('BBS', 'LOGFILE'))
    self.log.write('Connection from ' + self.user_ip + ' on Port ' + str(self.user_port))
    self.__debug("BBS Started", 1)
    self.time_login = time.time()
    self.subforum = 0
    self.msgno = 1
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
  HOST = 'localhost'
  PORT = 9999
  BUFSIZ = 1024
  MAX_CLIENTS = 5
  def __debug(self, message, level=1):
    if self.debug:
      self.debug.write(message, level)
  def __init__(self):
    self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  def accept_incoming_connections(self):
    """Sets up handling for incoming clients."""
    while True:
      client, address = self.server.accept()
      host, port = address
      self.__debug("Client connected from " + host + " on Port " + str(port), 2)
      #client.send(bytes("NAME?"))
      self.addresses[client] = address
      threading.Thread(target=self.handle_client, args=(client,)).start()
  def handle_client(self, client): 
    """Handles a single client connection."""
    try:
      name = str(client.recv(self.BUFSIZ))
    except Exception as x:
      self.__debug("Error " + str(x) + " communicating with client", 2)
      del self.clients[client]
      del self.addresses[client]
      return
    client.send(bytes("Type .quit to exit chat."))
    self.broadcast(bytes("%s has joined the chat!" % name))
    self.clients[client] = name
    while True:
      try:
        msg = client.recv(self.BUFSIZ)
      except Exception as x:
        msg = None
      if msg and msg != bytes(".quit"):
        self.broadcast(msg, name + ": ")
      else:
        client.close()
        del self.clients[client]
        self.broadcast(bytes("%s has left the chat." % name))
        host, port = self.addresses[client]
        del self.addresses[client]
        self.__debug("Client disconnected from " + host + " on Port " + str(port), 2)
        break
  def broadcast(self, msg, prefix=""):
    """Broadcasts a message to all the clients."""
    for sock in self.clients:
      sock.send(bytes(prefix) + msg)
  def start(self):
    self.threadid = threading.current_thread().ident
    self.debuglevel = 2
    self.debug = Debug(self.debuglevel, self.threadid)
    self.server.bind((self.HOST, self.PORT))
    self.__debug("Chat Server bound to " + self.HOST + " on Port " + str(self.PORT), 1)
    self.server.listen(self.MAX_CLIENTS)
    self.__debug("Waiting for connection...", 1)
    accept_thread = threading.Thread(target=self.accept_incoming_connections)
    accept_thread.start()  # Starts the infinite loop.
    accept_thread.join()
    self.server.close()

if __name__ == "__main__":
  config = Config()
  debug = config.getstr('SERVER', 'DEBUG')
  ipaddr = config.getstr('SERVER', 'IPADDR')
  port = config.getint('SERVER', 'PORT')
  debuglevel = config.getint('SERVER', 'DEBUG')
  debug = Debug(debuglevel)
  log = Log()
  log.open(config.getstr('SERVER', 'LOGFILE'))
  if config.getint('CHAT', 'CHAT'):
    chatServer = ChatServer()
    threading.Thread(target=chatServer.start).start()
  server = BBS_Server((ipaddr, port), BBS_Handler)
  ipaddr, port = server.server_address
  log.write('Server Opened on ' + ipaddr + ' Port ' + str(port))
  debug.write("Listening on {0:} port {1:}".format(ipaddr, port), 1)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    debug.write("\nCaught Keyboard Interrupt", 1)
    log.write('Server terminated by keyboard interrupt')
  print 'Exiting Server'
  quit()
