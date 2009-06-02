#!/usr/bin/env python
# encoding: utf-8
"""
csvparser.py

Created by Emil Erlandsson <emil@purplescout.se> on 2009-05-13.
Copyright (c) 2009 Purple Scout AB. All rights reserved.

This file is part of HarvestUtils.

HarvestUtils is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

HarvestUtils is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with HarvestUtils.  If not, see <http://www.gnu.org/licenses/>.
"""

import inspect
import logging
import os
import time
import unittest

log = logging.getLogger("csvparser")

class CSVFile(object):
  """
    This class represents a generic CSV-file and parses the file line by line.
    @param filepath is the path to the file
    @param clz is the class that should be instansiated with the parsed values
    @param skip_header is a boolean that is true if the first line is a 
           header and should be skipped
  """
  
  READ = 'r'
  WRITE = 'w'
  
  def __init__(self,filepath,cls,skip_header=True):
    self.file = self._open(filepath,None) 
    self.cls = cls
    # Determine the number of arguments to pass to the constructor (-1 for
    # self)
    self.length = len(inspect.getargspec(self.cls.__init__)[0]) - 1
    if skip_header:
      self.header = self.file.readline()
      log.debug("skip_header is True, throwing away: '%s'" % self.header)
    self.lineno = 0

  def next(self):
    self._open(self.file.name, CSVFile.READ)  # Just a check that we are in read-mode and at the right position.
    line = unicode(self.file.readline(), 'utf-8')
    if line:
      self.lineno+=1
      log.debug("CSVFile.next(): parsing line '%s'" % line.strip())
      return self._parse_line(line.strip())
    else:
      log.debug("CSVFile.next() reached end of file, starting from top next time")
      raise StopIteration

  def serialize(self,*args):
    self._open(self.file.name, CSVFile.WRITE)
    str = ""
    for arg in args:
      str = str + "%s," %arg
    str = str.rstrip(",")
    self.file.write("%s\n" % str)
    return str
    
  def _parse_line(self,line):
    args = line.split(",")
    args = [x.strip() for x in args]
    if not len(args) == self.length:
      log.warning("Number of parsed tokens is not equal to the predetermined number of tokens (%d,%d), line %d" % (len(args),self.length, self.lineno))
      log.warning("Throwing away line '%s'" % line)
      return self.next()
    else:
      return self.cls(*tuple(args))

  def _setoflines(self):
    curr = self.file.tell()
    self.file.seek(0)
    lines = [x.strip() for x in self.file.readlines()]
    self.file.seek(curr)
    return set(lines)

  def _open(self,filepath,mode):
    if mode is None:
      if os.path.exists(filepath):
        mode = CSVFile.READ
      else:
        mode = CSVFile.WRITE
      return file(filepath, mode)
    else:
      if not self.file.mode == mode:
        self.file = file(filepath,mode)

  def __iter__(self):
    return self

  def __sub__(self,other):
    if not isinstance(other,CSVFile):
      raise Exception, "Only two CSVFiles can be used for this operation"
    else:
      return self._setoflines() - other._setoflines()



# Unit test cases below this line
#----------------------------------------------------------------------------


class TestEntry(object):
  def __init__(self,a,b,c,d,e,f,g,h,i,j,k,l,m,n):
    self.args = tuple([a,b,c,d,e,f,g,h,i,j,k,l,m,n])

  def getargs(self):
    return self.args

  def printargs(self):
    print "Args:"
    num = 0
    for arg in self.args:
      num+=1
      print "- %d: '%s'" % (num,arg) 

class Dummy(object):
  def __init__(self,a,b,c):
    self.a = a
    self.b = b
    self.c = c

class Simple(object):
  def __init__(self,a):
    self.a = a

class TestCSVFile(unittest.TestCase):
  
  def setUp(self):
    self.DATAFILE = "./testdata/testdata.csv"
    self.OUTPUT = "./testdata/%s-testwrite.csv" % time.strftime("%Y-%m-%d_%H%M%S", time.localtime())

  def tearDown(self):
    if os.path.exists(self.OUTPUT):
      os.unlink(self.OUTPUT)

  def testGetFirstEntry(self):
    csvtest = CSVFile(self.DATAFILE, TestEntry)
    ent1 = csvtest.next()
    self.assertEquals("2007-01-01", ent1.getargs()[0])

  def testIteration(self):
    cvstest = CSVFile(self.DATAFILE, TestEntry)
    items = 0
    for e in cvstest:
      items+=1
    self.assertEquals(33,items,"There shall be 33 valid items in the file, there was %d" % items)

  def testSerialize(self):
    csvtest = CSVFile(self.OUTPUT, Dummy, skip_header=False) 
    csvtest.serialize("1","2","3")
    
    first = csvtest.next()
    self.assertEquals("1", first.a)
    self.assertEquals("2", first.b)
    self.assertEquals("3", first.c)
    
    csvtest.serialize("3","2","2")
    first = csvtest.next()
    self.assertEquals("3", first.a)
    self.assertEquals("2", first.b)
    self.assertEquals("2", first.c)

  def testDiff(self):
    self.TESTA = "./testdata/test_a"
    self.TESTB = "./testdata/test_b"

    a = CSVFile(self.TESTA, Dummy)
    b = CSVFile(self.TESTB, Dummy)

    self.assertEquals(set(['7','6']), b-a)

  def testDiffRead(self):
    self.TESTA = "./testdata/test_a"
    self.TESTB = "./testdata/test_b"

    a = CSVFile(self.TESTA, Simple)
    b = CSVFile(self.TESTB, Simple)

    diff = list(b-a)
    c = CSVFile(self.OUTPUT, Simple, skip_header=False)
    for d in diff:
      c.serialize(d)
    
    f = c.next()
    self.assertEquals('7', f.a)
    f = c.next()
    self.assertEquals('6', f.a)


if __name__ == "__main__":
  logging.basicConfig(level=logging.ERROR,format='%(asctime)s %(levelname)s %(message)s')
  unittest.main()

