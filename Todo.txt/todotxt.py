#!/usr/bin/env python
# encoding: utf-8
"""
todotxt.py

Created by Emil Erlandsson on 2011-02-09.
Copyright (c) 2011 Emil Erlandsson. All rights reserved.
"""
TESTDATA="""(B) +GarageSale @phone schedule Goodwill pickup
+GarageSale @home post signs around the neighborhood
2011-03-12 (A) @phone thank Mom for the meatballs
@shopping Eskimo pies +freaksale"""

import sys
import os
import re

class Todo(object):
	def __init__(self, string = ""):
		self.project = ""
		self.context = ""
		self.date = ""
		self.task = ""
		self.priority = ""
		if string is not "":
			self.parse(string)
	
	def parse(self, string):
		# extract priority (A-Z)
		m = re.match(".*(\([A-Z]\)).*", string)
		if m is not None:
			self.priority = m.group(1)
		
		# extract project\@[\w]*
		m = re.match(".*(\+[\w]*).*", string)
		if m is not None:
			self.project = m.group(1)
		
		# extract context
		m = re.match(".*(\@[\w]*).*", string)
		if m is not None:
			self.context = m.group(1)
		
		# extract date
		m = re.match(".*([\d]{4}-[\d]{2}-[\d]{2}).*", string)
		if m is not None:
			self.date = m.group(1)
			
		# Assume the rest is the task
		self.task = string.replace(self.priority, "").replace(self.project, "").replace(self.context, "").replace(self.date, "").strip()
			
	def __str__(self):
		#return "Task:\t\t%s\nPriority:\t%s\nProject:\t%s\nContext:\t%s\nDate:\t\t%s\n" % (self.task, self.priority, self.project, self.context, self.date)
		return ("%s %s %s %s %s" %  (self.priority, self.date, self.task, self.project, self.context)).strip().replace("  ", " ")
		
if __name__ == '__main__':
	projects = {}
	contexts = {}
	
	for line in TESTDATA.split("\n"):
		t = Todo(line)
		print t
		if not projects.has_key(t.project):
			projects[t.project] = []
		projects[t.project].append(t)
		
		if not contexts.has_key(t.context):
			contexts[t.context] = []
			
		contexts[t.context].append(t)
	
	print ""
	print "By project:"
	for prj in projects.keys():
		if prj == "":
			print "* No project assigned:"
		else:
			print "* %s:" % prj.replace("+", "")
		for task in projects[prj]:
			print "\t-%s" % task
			
	print ""
	print "By context:"
	for ctx in contexts.keys():
		if ctx == "":
			print "* No context assigned:"
		else:
			print "* %s:" % ctx
		for task in contexts[ctx]:
			print "\t-%s" % task
		

