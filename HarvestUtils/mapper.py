#!/usr/bin/env python
# encoding: utf-8
"""
mapper.py

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
import logging
import time

from config import cfg
from csvparser import CSVFile
from model import *

log = logging.getLogger("mapper")

class Mapper(object):
  
  def __init__(self, csvfile):
    pass
  
  def map(self):
    pass
    
    
class CSVDBMapper(Mapper):
  """
    This is were all the magic happends. All the entries in the csvfile
    parameter is read and fed to the database.
  """
  def __init__(self, csvfile):
    self.csv = CSVFile(csvfile, TimeEntry)
    self.done = False

  def map(self):
    if not self.done:
      ts = time.time()
      entries = 0
      for entry in self.csv:
        log.debug("Updating record (%d) %s" % (entries,entry))

        # 1) Check if the customer exists in DB, else create.
        q = Customer.query.filter_by(name=entry.customer)
        customer = q.first()  # If there should be multiple names, we ignore them
        if customer is None:
          customer = Customer(name=entry.customer)
          
        # 2) Check if the project exists in DB, else create.
        q = Project.query.filter_by(name=entry.project)
        q = q.filter(Project.customer.has(name=customer.name))
        project = q.first()  # If there should be multiple names, we ignore them
        if project is None:
          project = Project(name=entry.project)

        # 2.5) Set up relationship between customer and project
        customer.projects.append(project)

        # 3) Check if the employee exists in DB, else create.
        employee_str = "%s %s" % (entry.first_name, entry.last_name)
        q = Employee.query.filter_by(name=employee_str)
        employee = q.first()
        if employee is None:
          employee = Employee(name=employee_str)

        # 3.5) Set up relationsship between employee and project
        if not employee in project.employees:
          project.employees.append(employee)
        if not project in employee.projects:
          employee.projects.append(project)
        
        # 4) Skip check exists since it takes to much time. Just add to DB
        task = Task(name=entry.task,date=entry.date,hours=entry.hours,billable=entry.billable)
        task.employee = employee
        task.project = project
        entries+=1
 
        # 5) Commit and we are ready for a new one!
        #session.flush()
        session.commit()

      
      log.info("It took %d seconds to update %d entries." % (time.time()-ts, entries))
      done = True
    else:
      pass                     

class POMapper(Mapper):

  def __init__(self, csvfile):
    self.csv = CSVFile(csvfile, POEntry)
    self.done = False
  
  def map(self):
    if not self.done:
      ts = time.time()
      entries = 0
      for entry in self.csv:
        log.debug("Updating record (%d) %s" % (entries,entry))

        # 1) Check if the employee exists in DB, else create.
        employee_str = entry.employee
        q = Employee.query.filter_by(name=employee_str)
        employee = q.first()
        if employee is None:
          employee = Employee(name=employee_str)
        
        # 2) Create Purchase order
        po = PurchaseOrder(number=entry.number,start=entry.start,stop=entry.stop,price=entry.price,customer=entry.customer,reference=entry.reference)
        po.employee = employee
        entries+=1
        
        # 3) Set up relationship between employee and PO
        employee.pos.append(po)
        
        session.commit()

      
      log.info("It took %d seconds to update %d entries." % (time.time()-ts, entries))
      done = True
    else:
      pass
    
  
class CWMapper(Mapper):
  
  def __init__(self, csvfile):
    self.csv = CSVFile(csvfile, CWEntry)
    self.done = False
    
  def map(self):
    if not self.done:
      ts = time.time()
      entries = 0
      for entry in self.csv:
        log.debug("Updating record (%d) %s" % (entries,entry))

        # 1) Check if the employee exists in DB, else create.
        employee_str = entry.employee
        q = Employee.query.filter_by(name=employee_str)
        employee = q.first()
        if employee is None:
          employee = Employee(name=employee_str)
        
        # 2) Update employee number
        employee.number = entry.number
        
        # 3) Check if office exists in DB, else create.
        q = Office.query.filter_by(name=entry.office)
        office = q.first()
        if office is None:
          office = Office(name=entry.office)
        
        office.employees.append(employee)
        employee.office = office

        entries+=1
        session.commit()

      log.info("It took %d seconds to update %d entries." % (time.time()-ts, entries))
      done = True
    else:
      pass   