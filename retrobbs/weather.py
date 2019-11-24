#!/usr/bin/python2
#Retrieve ASII Weather Report from http://wttr.in

import re
import urllib2

class Weather():

  def __init__(self, debug=None):
    self.debug = debug

  def current(self, location):
    if location: 
      text = self.request(location)
      if text:  
        lines = self.filter(text)
        if lines[37][0:8] == "Location": return lines[0:7]
        else: return ['Location %s not found' % location]
      else:
        return ['Weather not available']
    else:
      return ['No Location Specified']
  
  def request(self, location):
    request = urllib2.Request('http://wttr.in/' + location)
    request.add_header('User-Agent', 'wget')
    try:
      response = urllib2.urlopen(request)
      return response.read()
    except StandardError as err:
      if self.debug: self.debug.write(err)
      return None
    
  def filter(self, text):
    text = re.sub('\x1B\[[0-9;]*m', '', text)
    text = re.sub('\xC2\xB0', '\xF8', text)     #Replace Degree Symbol
    text = re.sub('\xE2\x80\x95', '-', text)
    text = re.sub('\xE2\x80\x99', "'", text)
    text = re.sub('\xE2\x86\x90', 'W ', text)
    text = re.sub('\xE2\x86\x91', 'N ', text)
    text = re.sub('\xE2\x86\x92', 'E ', text)
    text = re.sub('\xE2\x86\x93', 'S ', text)
    text = re.sub('\xE2\x86\x96', 'NW', text)
    text = re.sub('\xE2\x86\x97', 'NE', text)
    text = re.sub('\xE2\x86\x98', 'SE', text)
    text = re.sub('\xE2\x86\x99', 'SW', text)
    return text.split('\n')

if __name__ == '__main__':
  weather = Weather()
  location = raw_input("Enter location: ")
  lines = weather.current(location)
  for line in lines: print(line)