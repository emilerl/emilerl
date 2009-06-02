#!/usr/bin/env python
# encoding: utf-8
"""
taskpaper.py

Created by Emil on 2009-06-02.
Copyright (c) 2009 Emil Erlandsson

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.  
"""

import sys
import os  

class TaskPaperProject(object):
  """Representing a project in a TaskPaper file"""
  def __init__(self, line):
    self.line = line
    self.name = ""
    self.tasks = []  
    self.notes = []
    self.__parse()
  
  def __parse(self):
    """Parses the line and sets up variables"""
    self.name = self.line[:-1]
   
  def add_note(self, note):
    """Adds a note to this project"""
    self.notes.append(note)
    
  def add_task(self, task):
    """Adds a task to this project"""
    self.tasks.append(task)
                          
                          
class TaskPaperTask(object):
  """Represents a task in a taskpaper"""
  def __init__(self, line):
    self.line = line       
    self.tags = []
    self.project = None 
    self.name = ""
    self.notes = []
    self.__parse() 
  
  def __parse(self):
    """Parses the line and sets up variables"""
    tokens = self.line.replace("- ", "").split("@")
    self.name = tokens[0]
    self.tags = tokens[1:]
  
  def set_project(self, project):
    self.project = project

  def add_note(self, note):
    """Adds a note to this project"""
    self.notes.append(note)
    
  def add_tag(self, tag):
    self.tags.append(tag)
  

class TaskPaper(object):
  """A wrapper class for TaskPaper files"""
  def __init__(self, filename):
    self.filename = filename
    self.projects = []
    self.tasks = []       

  def add_task(self, task):
    """Adds a no-parent task to this task paper"""
    self.tasks.append(task)
  
  def add_project(self, project):
    """Adds a project to the taskpaper"""
    self.projects.append(project)

  def __str__(self):
    return "TaskPaper with %d headless tasks and %d projects" \
    % (len(self.tasks), len(self.projects)) 
    
  def print_entries(self):
    """Prints all entries in the task paper"""
    
    print "Taskpaper: %s" % self.filename
    
    for project in self.projects:
      print "\n%s:" % project.name
      for note in project.notes:
        print note
        
      for task in project.tasks:
        rep = "- %s" % task.name.strip()
        for tag in task.tags:
          rep += " @%s" % tag.strip()
        print rep
        for note in task.notes:
          print "%s" % note
    print "\n\n"
    
  def print_stats(self): 
    tasks = len(self.tasks)
    notes = 0
    
    for project in self.projects:
      tasks += len(project.tasks)
      notes += len(project.notes)
      for task in project.tasks:
        notes += len(task.notes)
    
    print "%s has: %d projects with %d tasks and %d notes." \
    % (self.filename, len(self.projects), tasks, notes)
    


def parse_task_paper(filename):
  """Parsing of a TaskPaper file"""
  handle = file(filename)
  
  taskpaper = TaskPaper(filename)
  project = None
  last = None
  for line in handle.readlines():
    line = unicode(line.strip(), "utf-8")
    
    if line.startswith("- "): # It is a task
      task = TaskPaperTask(line)
      last = task
      if project is not None:
        project.add_task(task)
        task.project = project         
        
    elif line.endswith(":"): # It is a project
      project = TaskPaperProject(line)
      taskpaper.add_project(project)  
      last = project
      
    else:                    # It is a note
      last.add_note(line)
  
  return taskpaper
    

if __name__ == '__main__':  
  tp = parse_task_paper(sys.argv[1]) 
  tp.print_entries() 

