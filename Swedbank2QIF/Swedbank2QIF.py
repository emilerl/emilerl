#!/usr/bin/env python
# encoding: utf-8
"""
swedbank2qif.py

Created by Emil on 2009-08-03.
Copyright (c) 2009 Emil Erlandsson <emil@buglix.org>. All rights reserved.
"""

import re
import sys
import os

# Created with RegExr 0.3b at http://gskinner.com/RegExr/
PATTERN = ".*([0-9][0-9]-[0-9][0-9]-[0-9][0-9])         ([0-9][0-9]-[0-9][0-9]-[0-9][0-9])           (.*)                    (-?[0-9 ]*,[0-9 ][0-9 ]).*"

def main(qif):
  if not os.path.exists(qif):
    print("Error: '%s' does not exist!")
    sys.exit(1)
  else:
    handle = file(qif)
    tempfile = file(qif+".qif", 'w')
    
    reg = re.compile(PATTERN)
    for line in handle.readlines():
      line = unicode(line, 'ascii', "ignore")
      m = reg.match(line)
      if m is not None:
        booking_date = m.group(1)
        transaction_date = m.group(2)
        description = m.group(3)
        amount = float(m.group(4).replace(' ', '').replace(',', '.'))
        
        tempfile.write("!Type:Bank\n")
        tempfile.write("P%s\n" % description)
        tempfile.write("T%f\n" % amount)
        tempfile.write("D%s\n" % transaction_date)
        tempfile.write("^\n")

if __name__ == '__main__':
  if len(sys.argv) is not 2:
    print "Usage. python swedbank2qif.py <transactions>.txt"
    sys.exit(1)
  else:
    main(sys.argv[1])

