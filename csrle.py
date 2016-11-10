#!/usr/bin/python

from graphics import *

rleFile = "../rle/albert.rle"
with open(rleFile, mode='rb') as file:
  rleString = file.read()

print rleString.encode('string-escape')
i = rleString.find('\x1bGH')
if i < 0:
  print "Illegal RLE File"
  exit()
rleData = rleString[i+3:]

width = 256
height = 192
foreground = 'black'
background = 'white'
#foreground, background = background, foreground

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
win.getMouse()
win.close()
print x, y
