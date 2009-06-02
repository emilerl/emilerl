#!/usr/bin/env python
# encoding: utf-8
"""
update_db.py

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
import sys

from config import cfg
from mapper import CSVDBMapper, POMapper, CWMapper   
from model import TimeEntry, POEntry, CWEntry

log = logging.getLogger("update_db")

def _get_mapper(path):
  handle = file(path, 'r')
  length = len(handle.readline().split(","))   
  
  if length is len(inspect.getargspec(TimeEntry.__init__)[0]) - 1:
    log.info("File %s contains %d fields, it is a Harvest file" % (path, length))
    return CSVDBMapper(path)
  elif length is len(inspect.getargspec(POEntry.__init__)[0]) - 1:
    log.info("File %s contains %d fields, it is a PurchaseOrder file" % (path, length))
    return POMapper(path)
  elif length is len(inspect.getargspec(CWEntry.__init__)[0]) - 1:
    log.info("File %s contains %d fields, it is a CoWorker file" % (path, length))
    return CWMapper(path)
  else:
    log.warning("File %s contains %d fields, it is of UNKNOWN type!" % (path, length))
    return None

if __name__ == "__main__":
  logging.basicConfig(level=cfg['loglevel'],format=cfg['logformat'])
  if len(sys.argv) > 1:
    
    for csvfile in sys.argv[1:]:
      if os.path.exists(csvfile):
        log.info("Starting to map %s to the DB" % csvfile)
        mapper = _get_mapper(csvfile)
      
        if mapper is not None:
          mapper.map()
        else:
          log.error("Unknown file format for %s" % csvfile)
      else:
        log.error("File %s does not exist. Exiting" % csvfile)

  else:
    print "Usage: update_db.py <csvfile>"
