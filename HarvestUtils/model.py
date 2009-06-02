#!/usr/bin/env python
# encoding: utf-8
"""
model.py

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

from elixir import *
import unittest

from csvparser import CSVFile

class Customer(Entity):
  name = Field(Unicode(50), unique=True)
  projects = OneToMany('Project')
  
  def __repr__(self):
    return '<Customer "%s">' % self.name

class Project(Entity):
  name = Field(Unicode(50))
  customer = ManyToOne('Customer')
  employees = ManyToMany('Employee')
  tasks = OneToMany('Task')

  def __repr__(self):
    return '<Project "%s">' % self.name

class Office(Entity):
  name = Field(Unicode(50))
  employees = OneToMany('Employee')

class PurchaseOrder(Entity):
  number = Field(Integer())
  start = Field(Date())     
  stop = Field(Date())
  price = Field(Integer())
  customer = Field(Unicode(50)) 
  reference = Field(Unicode(50))
  employee = ManyToOne('Employee') 

class Employee(Entity):
  name = Field(Unicode(50), primary_key=True)
  number = Field(Integer)
  projects = ManyToMany('Project')
  tasks = OneToMany('Task')
  office = ManyToOne('Office')
  pos = OneToMany("PurchaseOrder")
  
  def __repr__(self):
    return '<Employee "%s">' % self.name


class Task(Entity):
  name = Field(Unicode(50))
  date = Field(Date())
  hours = Field(Float())
  billable = Field(Boolean())
  employee = ManyToOne('Employee')
  project = ManyToOne('Project')

  def __repr__(self):
    return '<Task "%s - %s %0.2f hours at %s">' % (self.date, self.employee.name, self.hours,self.name)
  
class POEntry(object):
  """
    A data class that holds information from a Purchase Order CSV file.
    employee,customer,reference,price,start,stop,po-number
  """
  def __init__(self,employee,customer,reference,price,start,stop,number):
    self.employee = employee
    self.customer = customer
    self.reference = reference
    self.price = price
    self.start = start
    self.stop = stop
    self.number = number

class CWEntry(object):
  def __init__(self,employee,number,office):
    self.employee = employee
    self.number = number
    self.office = office
    
class TimeEntry(object):
  """
    Just a simple data class for holding a time record from the CSV file.
    NOT to be confused with the rest of the data model.
    # The first row of the file is a header that can be ignored.
    # A CSV-line from Havest contains the following fields:
    #  1)  Date in YYYY-MM-DD format
    #  2)  Customer
    #  3)  Project
    #  4)  Project Code (unused)
    #  5)  Task
    #  6)  Note (text field with comments)
    #  7)  Hours
    #  8)  First name of reporter
    #  9)  Last name of reporter
    # 10)  Hours billable (billable | non-billable)
    # 11)  Employee or contractor (employee | contractor )
    # 12)  Approved (yes | no)
    # 13)  Hourly rate as float
    # 14)  Cost as float
    # 15)  Department

  """
  def __init__(self,date,customer,project,project_code,task,note,hours,first_name,last_name,billable,evsc,approved,rate,cost,department):
    self.date = date
    self.customer = customer
    self.project = project
    self.project_code = project_code
    self.task = task
    self.note = note
    self.hours = float(hours)
    self.first_name = first_name
    self.last_name = last_name
    if billable == "billable":
      self.billable = True
    else:
      self.billable = False
    if evsc == "employee":
      self.evsc = True
    else:
      self.evsc = False
    if approved == "yes":
      self.approved = True
    else:
      self.approved = False
    self.rate = float(rate)
    self.cost = float(cost)
    #self.digest = self._calcdigest()
    self.department = department
  
  def _calcdigest(self):
    import md5
    str = "%s%s%s%s%s%s%s%s" % (self.date,self.customer,self.project,self.task,self.hours,self.first_name,self.last_name,self.billable)
    hexdigest=md5.md5(str.encode('iso-8859-1')).hexdigest()
    return unicode(hexdigest, 'utf-8')

  def __str__(self):
    return "%s - %s %s, %0.2f hours at %s working with %s" % (self.date, self.first_name, self.last_name, self.hours, self.customer, self.task) 


# Unit tests below
#----------------------------------------------------------------------------

class TestTimeEntry(unittest.TestCase):

  def setUp(self):
    self.DATAFILE = "testdata/testdata.csv"
  
  def testparse(self):
    csv = CSVFile(self.DATAFILE, TimeEntry)
    for entry in csv:
      self.assertEquals(0.0, entry.cost * entry.rate, "The cost and rate is always 0.0")
      self.assertEquals("200", entry.date[:3], "The first three chars should be 200")
    

if __name__ == "__main__":
  unittest.main()
else:
  from config import cfg
  metadata.bind = cfg['db.bind']
  setup_all(True)
