#!/usr/bin/env python
#
# pyphoon - Phase of the Moon (Python version)
# Igor Chubin <igor@chub.in>, 05.03.2016, 
#
# Based on the original version of Jef Poskanzer <jef@mail.acme.com>
# written in Pascal in 1979 (and later translated to C)
#

import sys
import os
import argparse
import datetime
import dateutil.parser
import time
import locale

from math import cos, sqrt

from astro import unix_to_julian, phase, phasehunt2
from moons import background6, background18, background19, background21, background22, background23, background24, background29, background32
from translations import LITS

#
# Global defines and declarations.
#
SECSPERMINUTE = 60
SECSPERHOUR = (60 * SECSPERMINUTE)
SECSPERDAY = (24 * SECSPERHOUR)

PI = 3.1415926535897932384626433

DEFAULTNUMLINES = 23
DEFAULTNOTEXT = False

QUARTERLITLEN = 16
QUARTERLITLENPLUSONE = 17

# If you change the aspect ratio, the canned backgrounds won't work.
ASPECTRATIO = 0.5

def fatal( message ):
    print >>sys.stderr, message
    sys.exit(1)
    

class Odphoon:

    def putseconds(self, secs ):
        days = int(secs / SECSPERDAY)
        secs = int(secs - days * SECSPERDAY)
        hours = int(secs / SECSPERHOUR)
        secs = int(secs - hours * SECSPERHOUR)
        minutes = int(secs / SECSPERMINUTE)
        secs = int(secs - minutes * SECSPERMINUTE)
    
        return "{:d} {:2d}:{:02d}:{:02d}".format(days, hours, minutes, secs)
    
    def putmoon(self, t=time.time(), numlines=DEFAULTNUMLINES, atfiller='@', notext=DEFAULTNOTEXT, lang=None ):
        
        output = []
        def putchar(c):
          output[0] += c
        def fputs(s):  
          output[0] += s
    
        if not lang:
            try:
                lang = locale.getdefaultlocale()[0]
            except: 
                lang = 'en'
    
        if lang not in LITS and '_' in lang:
            lang = lang.split('_', 1)[0]
    
        lits = LITS.get(lang, LITS.get('en'))
        qlits = [ x + " +" for x in lits ]
        nqlits = [ x + " -" for x in lits ]
    
        # Find the length of the atfiller string
        atflrlen = len( atfiller )
    
        # Figure out the phase
        jd = unix_to_julian( t )
        pctphase, cphase, aom, cdist, cangdia, csund, csuang = phase( jd )
        angphase = pctphase * 2.0 * PI
        mcap = -cos( angphase )
    
        # Figure out how big the moon is
        yrad = numlines / 2.0
        xrad = yrad / ASPECTRATIO
        numcols = xrad * 2
      
        # Figure out some other random stuff
        midlin = int(numlines / 2)
        phases, which = phasehunt2( jd )
      
        # Now output the moon, a slice at a time
        atflridx = 0
        lin = 0
        while lin < numlines:
            line = ""        
        
            # Compute the edges of this slice
            y = lin + 0.5 - yrad
            xright = xrad * sqrt( 1.0 - ( y * y ) / ( yrad * yrad ) )
            xleft = -xright
            if ( angphase >= 0.0 and angphase < PI ):
                xleft = mcap * xleft
            else:
                xright = mcap * xright
    
            colleft = int(xrad + 0.5) + int(xleft + 0.5)
            colright = int(xrad + 0.5) + int(xright + 0.5)

            # Now output the slice
            col = 0
            while col < colleft:
              line += ' '
              col += 1
            while col <= colright:
              if 6 == numlines:
                  c = background6[lin][col]
              elif 18 == numlines:
                  c = background18[lin][col]
              elif 19 == numlines:
                  c = background19[lin][col]
              elif 21 == numlines:
                  c = background21[lin][col]
              elif 22 == numlines:
                  c = background22[lin][col]
              elif 23 == numlines:
                  c = background23[lin][col]
              elif 24 == numlines:
                  c = background24[lin][col]
              elif 29 == numlines:
                  c = background29[lin][col]
              elif 32 == numlines:
                  c = background32[lin][col]
              else:
                  c = '@'
              if c != '@':
                line += c
              else:
                line += atfiller[atflridx]
                atflridx = ( atflridx + 1 ) % atflrlen
              col += 1

            #Fill end of slice with spaces
            while col <= numcols:
              line += ' '
              col += 1
    
            if (numlines <= 27 and not notext):
              # Output the end-of-line information, if any
              line += '  '
              if lin == midlin - 2:
                line += qlits[int(which[0] * 4.0 + 0.001)] 
              elif lin == midlin - 1:
                line += self.putseconds( int( ( jd - phases[0] ) * SECSPERDAY ) ) 
              elif lin == midlin:
                line += nqlits[int(which[1] * 4.0 + 0.001)] 
              elif lin == midlin + 1:
                line += self.putseconds( int( ( phases[1] - jd ) * SECSPERDAY ) ) 
    
            output.append(line)
            lin += 1
    
        return output

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Show Phase of the Moon')
    parser.add_argument('-n','--lines', help='Number of lines to display (size of the moon)', required=False, default=DEFAULTNUMLINES)
    parser.add_argument('-x','--notext', help='Print no additional information, just the moon', required=False, default=DEFAULTNOTEXT, action="store_true")
    parser.add_argument('date', help='Date for that the phase of the Moon must be shown. Today by default', nargs='?', default=time.strftime("%Y-%m-%d %H:%M:%S"))
    parser.add_argument('-l', '--language', help='locale for that the phase of the Moon must be shown. English by default', nargs='?', default=None)
    args = vars(parser.parse_args())
    
    try:
        d = time.mktime( dateutil.parser.parse(args['date']).timetuple() )
    except Exception as e:
        fatal("Can't parse date: {}".format(args['date']))
    
    try:
        n = int( args['lines'] )
        lang = args['language']
    except Exception as e:
        print(e)
        fatal("Number of lines must be integer")
    
    try:
        notext = bool( args['notext'] )
    except Exception as e:
        print(e)
    
    print('\n'.join(Odphoon().putmoon( d, n, '@', notext, lang)))
