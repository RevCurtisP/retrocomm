#!/usr/bin/python

from graphics import *
import os
import tkFileDialog
import tkMessageBox

configFileName = os.path.expanduser('~') + "/.csrle"

def drawRle(rleData):
  width = 256
  height = 192
  foreground = 'black'
  background = 'white'
  win = GraphWin("Compuserve RLE", width, height)
  win.setBackground(background)
  x = 0
  y = 0
  p = True
  for c in rleData:
    z = ord(c) - 32
    if z < 0:
      continue
    while z > 0:
      if p:
        win.plot(x, y, foreground)
      x += 1
      if x >= width:
        y += 1
        x = 0
      z -= 1
    p = not p
    if win.checkMouse(): break
  win.getMouse()
  win.close()

def readConfig():
  config = ""
  if os.path.isfile(configFileName):
    with open(configFileName) as configFile:
      config = configFile.read()
  return config

def writeConfig(config):
  with open(configFileName, mode='w') as configFile:
    configFile.write(config)

def getRleFileName():
  typeList = [("RLE Files", (".rle",".RLE"))]
  rleDir = readConfig()
  rleFileName = tkFileDialog.askopenfilename(filetypes=typeList, initialdir=rleDir)
  if rleFileName: 
    newDir = os.path.dirname(rleFileName)
    writeConfig(newDir)
  return rleFileName
  
def readRleFile(rleFileName):
  with open(rleFile, mode='rb') as file:
    rleString = file.read()
  i = rleString.find('\x1bGH') #Find Start Sequence
  if i < 0:
    tkMessageBox.showwarning("Error", "Invalid Compuserve RLE File")
    return ""
  rleData = rleString[i+3:]
  i = rleData.find('\x1bGN') #Find End Sequence
  if i > 0: 
    rleData = rleData[:i]
  return rleData
  
while True:
  rleFile = getRleFileName()
  if rleFile == '':
    exit()
  rleData = readRleFile(rleFile)
  if rleData != '':
    drawRle(rleData)

