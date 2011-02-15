#!/usr/bin/env python 

import getpass, imaplib, email
import sys
from dateutil import parser

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'



def print_details(data, string = "answer"):
	msg = email.message_from_string(data)
	m_from = msg["From"]
	m_subject = msg["Subject"].replace("Fw:","").replace("Fwd:", "").replace("Re:","").replace("FW:", "")
	m_from = m_from.split("<")[0].strip().replace('"', "")
	d = parser.parse(msg["date"])
	print bcolors.OKBLUE + "* %s" % d + bcolors.ENDC + " - " + string + " " + bcolors.OKGREEN + "%s"% m_from +bcolors.ENDC+ " re:" + bcolors.FAIL + " %s" % m_subject +bcolors.ENDC

M = imaplib.IMAP4_SSL(sys.argv[1])
M.login(sys.argv[2], getpass.getpass())
M.select()
print "Messages marked todo"
print "===================="
typ, data = M.search(None, 'Keyword', "$label4")
for num in data[0].split():
	typ, data = M.fetch(num, '(BODY[HEADER])')	
	print_details(data[0][1])

print "Unread messages"
print "==============="
typ, data = M.search(None, 'UnSeen')
for num in data[0].split():
	typ, data = M.fetch(num, '(BODY.PEEK[HEADER])')	
	print_details(data[0][1], "check")


M.close()
M.logout()