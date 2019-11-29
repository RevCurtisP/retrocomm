#!/usr/bin/python2
#Retrieve ASII Weather Report from http://wttr.in

import re
import urllib2
import types

class Weather():

  def __init__(self, debug=None):
    self.debug = debug

  def __debug(self, message, level=1):
    if self.debug:
      self.debug.write('Weather: ' + message, level)

  def __debugLines(self, lines, level=2):
    if self.debug:
      lineno = 1
      for line in lines:
        self.debug.write('%d: %s' %(lineno, line))
        lineno += 1

  def current(self, location):
    if location: 
      text = self.request(location)
      if text:  
        self.__debug('Received text %s' % text,5)
        lines = self.filter(text)
        self.__debugLines(lines, 4)
        if len(lines) > 37 and lines[37][0:8] == "Location": 
          return lines[0:7]
        else: 
          return ['Location %s not found' % location]
      else:
        return ['Weather not available']
    else:
      return ['No Location Specified']
  
  def request(self, location):
    self.__debug('Requesting report for "%s"' % location, 3)
    request = urllib2.Request('http://wttr.in/' + location)
    request.add_header('User-Agent', 'wget')
    try:
      response = urllib2.urlopen(request)
      return response.read()
    except StandardError as err:
      self.__debug(err)
      return None
    
  def filter(self, text):
    text = re.sub('\x1B\[[0-9;]*m', '', text)   #Remove ANSI Codes
    text = re.sub('\xC2\xB0', ' ', text)     #Degree Symbol
    text = re.sub('\xE2\x80\x95', '-', text)
    text = re.sub('\xE2\x80\x98', "'", text)    
    text = re.sub('\xE2\x80\x99', "'", text)    #Rain
    text = re.sub('\xE2\x86\x90', 'W ', text)   #Replace Arrows
    text = re.sub('\xE2\x86\x91', 'N ', text)
    text = re.sub('\xE2\x86\x92', 'E ', text)
    text = re.sub('\xE2\x86\x93', 'S ', text)
    text = re.sub('\xE2\x86\x96', 'NW', text)
    text = re.sub('\xE2\x86\x97', 'NE', text)
    text = re.sub('\xE2\x86\x98', 'SE', text)
    text = re.sub('\xE2\x86\x99', 'SW', text)
    text = re.sub('mph ', 'mph', text)          #Compensate for added space
    text = re.sub('\xE2\x94[\x80]', '-', text)  #Line Draw Characters
    text = re.sub('\xE2\x94[\x82]', '|', text)
    text = re.sub('\xE2\x94[\x8C\x90\x94\x98\x9C\xA4\xAC\xB4\xBC]', '+', text)
    return text.split('\n')

if __name__ == '__main__':
  weather = Weather()
  location = raw_input("Enter location: ")
  lines = weather.current(location)
  for line in lines: print(line)
