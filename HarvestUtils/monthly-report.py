#!/usr/bin/env python
# encoding: utf-8
"""
monthly-report.py

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

import sys
import datetime
from time import strptime, strftime    

from model import *
from config import cfg
from statistics_month import DateModel

# Code from
# http://code.activestate.com/recipes/521915/
# Recipe 521915: start date and end date of given week      
# Snippet start
def _getWeekDetails(_weekNo, _Year, _weekStart): 
  _weekNo = _weekNo - 1  # Quickfix for 2009
  rslt = []
  janOne = strptime('%s-01-01' % _Year, '%Y-%m-%d')
  dayOfFirstWeek = ((7-int((strftime("%u",janOne)))+ int(_weekStart)) % 7)
  if dayOfFirstWeek == 0:
    dayOfFirstWeek = 7
  dateOfFirstWeek = strptime('%s-01-%s' % (_Year, dayOfFirstWeek), '%Y-%m-%d')
  dayOne = datetime.datetime( dateOfFirstWeek.tm_year, dateOfFirstWeek.tm_mon, dateOfFirstWeek.tm_mday )
  daysToGo = 7*(int(_weekNo)-1)
  lastDay = daysToGo+6
  dayX = dayOne + datetime.timedelta(days = daysToGo)
  dayY = dayOne + datetime.timedelta(days = lastDay)
  resultDateX = strptime('%s-%s-%s' % (dayX.year, dayX.month, dayX.day), '%Y-%m-%d')
  resultDateY = strptime('%s-%s-%s' % (dayY.year, dayY.month, dayY.day), '%Y-%m-%d')
  rslt.append(resultDateX)
  rslt.append(resultDateY)
  return rslt   
# Snippet end
                       
class MonthlyReport(object):
  def __init__(self, period):
    self.month = "%s-01" % period
    self.date = DateModel(self.month)
    self.start = self.date.get_month_start()
    self.stop = self.date.get_month_stop()
    self.period = cfg['purple_heart'][int(period.split("-")[1])]
          
  def get_report(self):
    "Return a string ready to be printed." 
    
    total_time = 0
    total_billable = 0
    office_time = {}
    not_active = []  # Employees with no time entries at all
    incomplete = []  # Employees with some entries, but not enough
    
    result_header = "Billing report for %s to %s (%d days total)\n\n" % (self.start, self.stop, cfg['daysofmonth'][self.date.get_month_number()])  
    result_stats = ""
    result_rpt = ""

    # x.name.encode('utf-8')
    employees = Employee.query.order_by(Employee.number)

    for employee in employees:
      entries = self._get_employee_entries(employee.name.encode("utf-8"))
      
      if len(entries.keys()) > 0:
        total = 0
        avail = 0
        billable = 0
        eno = -1
        if employee.number is not None:
          eno = employee.number
        result_rpt += ":: %s (%d) ::\n\n- Reported time\n" % (employee.name.encode("utf-8"), eno)
        for customer in entries.keys():
          for project in entries[customer].keys():
            for task in entries[customer][project].keys():
              result_rpt += "\t* %s / %s / %s:%0.2f\n" % (customer, project, task, entries[customer][project][task])
              if task in cfg["billable"]:
                billable += entries[customer][project][task]
              
              if task in cfg["absence"]:
                avail -=  entries[customer][project][task]
                
              total += entries[customer][project][task]
        result_rpt += "\t* Total time reported: %0.2f\n" % total
        
        
        available = cfg['daysofmonth'][self.date.get_month_number()] * 8
        if cfg['parttime'].has_key(employee.name.encode("utf-8")):
          available = available * cfg['parttime'][employee.name.encode("utf-8")]
        
        total_time += available + avail
        total_billable += billable
        
        office = "No office"
        if employee.office is not None:
          office = employee.office.name.encode('utf-8')
        if not office_time.has_key(office):
          office_time[office] = { "total": 0, "billable": 0 }
        
        office_time[office]["total"] += available + avail
        office_time[office]["billable"] += billable
        
          
        if total < available:
          incomplete.append((employee, (available-total)))
          
        pos = PurchaseOrder.query.filter(PurchaseOrder.start <= self.stop)
        pos = pos.filter(PurchaseOrder.stop >= self.start)
        pos = pos.filter(PurchaseOrder.employee == employee)
        
        result_rpt += "\n- Purchase orders\n"
        if pos.first() is not None:
          
          for po in pos:
             result_rpt += "\t- %s (%s)\n" % (po.customer.encode("utf-8"), po.reference.encode("utf-8"))  
             result_rpt += "\t\t* PO-number: %s\n" % str(po.number).encode("utf-8")
             result_rpt += "\t\t* Period: %s to %s\n" % (po.start, po.stop) 
             result_rpt += "\t\t* Price: %0.2f SEK/hour\n" % (po.price) 
        else:
           result_rpt +=  "\t * NO PURCHASE ORDERS FOUND!\n"
        
        result_rpt += "\n- Billing ratio\n"
        result_rpt += "\t* Billable hours: %0.2f\n" % billable
        result_rpt += "\t* Available hours: %0.2f\n" % (available + avail)
        result_rpt += "\t* Ratio: %d percent\n" % ((billable/(available+avail))*100)
        
        result_rpt += "\n- Salary information\n"
        purple_hearts = 0
        overtime = 0
        for week in self.period:
          winfo = _getWeekDetails(week, 2009, 2)
          weekstart = strftime("%Y-%m-%d", winfo[0])                     
          weekstop = strftime("%Y-%m-%d", winfo[1])
          result_rpt += "\t - Week %d from %s to %s\n" % (week, weekstart, weekstop)
          
          tasks = Task.query.filter(Task.date >= weekstart) 
          tasks = tasks.filter(Task.date <= weekstop)
          tasks = tasks.filter(Task.employee == employee)
          
          week_total = 0
          week_billable = 0
          for task in tasks:
            if not task.name == "Kompledighet":
              week_total += task.hours
            
            if task.name.encode("utf-8") in cfg["billable"]:
               week_billable += task.hours            
            
            if task.project.name == "Internal" and task.name != "Kompetensutveckling":
              result_rpt += "\t\t * %s %s - %0.2f hours\n" % (task.name.encode("utf-8"), task.date, task.hours)
            
            if task.name == "Komptid" or task.name == "Uttag av komp":
              week_total = week_total - task.hours
          
          normal_time = cfg['normal_time']
          if cfg['parttime'].has_key(employee.name.encode("utf-8")):
            normal_time = normal_time * cfg['parttime'][employee.name.encode("utf-8")]
          
          otime = week_total - normal_time
          result_rpt += "\t\t * Övertid: %0.2f hours\n" %  otime
          overtime += otime   
            
          result_rpt += "\t\t * Purple Heart time - %0.2f hours\n" % (week_billable)
            
          if week_billable >= cfg["normal_time"]:
            purple_hearts += 1
          
          result_rpt +=  "\t\t * Weekly total: %0.2f hours\n\n" % (week_total)
        
        result_rpt += "\t - Övertidsdelta: %0.2f hours\n\n" % (overtime)
        extra = 1
        if purple_hearts == len(self.period):
          extra = 2
        result_rpt += "\t - Purple Hearts: %d of %d = %d kr\n" % (purple_hearts, len(self.period), (purple_hearts*350) * extra )   
        
        result_rpt += "\n\n\n"
      else:
        not_active.append(employee.name.encode("utf-8"))
      
    result_stats = "- Billing ratio\n\t- Company total\n\t\t* Available time: %0.2f\n\t\t* Billable time: %0.2f\n\t\t* Ratio: %d percent\n" %  (total_time, total_billable, ((total_billable/total_time)*100))
    
    for office in office_time.keys():
      result_stats += "\t- %s\n\t\t* Available time: %0.2f\n\t\t* Billable time: %0.2f\n\t\t* Ratio: %d percent\n" % (office, office_time[office]["total"], office_time[office]["billable"], ((office_time[office]["billable"]/office_time[office]["total"])*100))
    
    if len(incomplete) > 0:
      result_stats += "\n\n- Incomplete reports\n"
    for emp, hours in incomplete:
      result_stats += "\t* %s is missing %0.2f hours\n" % (emp.name.encode('utf-8'), hours)
    
    result_stats += "\n\n"
    
    return result_header + result_stats + result_rpt

  def _get_employee_entries(self,employee):
    tasks = Task.query.filter(Task.date >= self.start)
    tasks = tasks.filter(Task.date <= self.stop)
    tasks = tasks.filter(Task.employee.has(name=unicode(employee,"utf-8")))
    return self._aggregate_by_customer(tasks)

  def _aggregate_by_customer(self, tasks):
    result = {}
    for task in tasks:
      customer =  task.project.customer.name.encode("utf-8")
      project =  task.project.name.encode("utf-8")
      task_name = task.name.encode("utf-8")

      if not result.has_key(customer):
        result[customer] = {}

      if not result[customer].has_key(project):
        result[customer][project] = {}

      if not result[customer][project].has_key(task_name):
        result[customer][project][task_name] = 0

      result[customer][project][task_name] += task.hours
    return result

if __name__ == "__main__":
  if len(sys.argv) == 1:
    print "Usage: python monthly-report.py YYYY-MM"
  else:
    report = MonthlyReport(sys.argv[1])
    print report.get_report()
