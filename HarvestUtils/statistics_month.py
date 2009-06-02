#!/usr/bin/env python
# encoding: utf-8
"""
statistics_month.py

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

import calendar
import time
import sys

from model import *

class Statistics(object):

  def __init__(self,datemodel):
    if not isinstance(datemodel, DateModel):
      raise Exception, "This class needs a DateModel instance as first argument"
    self.date = datemodel
    self.start = self.date.get_month_start()
    self.stop = self.date.get_month_stop()

  def by_employee(self,employee):
    tasks = Task.query.filter(Task.date >= self.start)
    tasks = tasks.filter(Task.date <= self.stop)
    tasks = tasks.filter(Task.employee.has(name=employee))
    return self._aggregate_tasks(tasks)

  def by_task(self,name):
    pass

  def _aggregate_tasks(self,tasks):
    """
      Merge the hours for a number of tasks by name, return a dict with task name as key.
    """
    result = {}
    for task in tasks:
      #print "Adding %0.2f hours to %s" % (task.hours, task.name)
      if not result.has_key(task.name):
        result[task.name] = task.hours
      else:
        result[task.name] += task.hours

    return result


class DateModel(object):

  def __init__(self,date=None):
    if date is None:
      self.date = time.strftime("%Y-%m-%d", time.localtime())
    else:
      self.date = date
    self.year =  int(self.date.split("-")[0])
    self.month = int(self.date.split("-")[1])
    self.day = int(self.date.split("-")[2])
    self.cal = calendar.Calendar()
    self.days = max(self.cal.itermonthdays(self.year,self.month))

  def get_month_start(self):
    return  "%d-%02d-01" % (self.year,self.month)

  def get_month_stop(self):
    return "%d-%02d-%d" % (self.year,self.month,self.days)

  def get_init_date(self):
    return self.date

  def get_month_number(self):
    return self.month

  def next(self):
    month = self.month + 1
    year = self.year
    if month == 13:
        month = 1
        year += 1
    return DateModel("%s-%s-%s" % (year, month, self.day))


if __name__ == "__main__":
  mod = DateModel(sys.argv[2]) # Create a date model with current date as seed.
  stats = Statistics(mod)
  print "Start %s, Stop %s" % (mod.get_month_start(), mod.get_month_stop())
  stat = stats.by_employee(unicode(sys.argv[1], 'utf-8'))
  total = 0
  print "Hours by task:"
  for act, hours in stat.items():
    print " - %s: %0.2f" % (act, hours)
    total += hours
  print "Totalt hours: %0.2f" % total
