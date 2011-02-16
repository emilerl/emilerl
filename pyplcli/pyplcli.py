#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by Emil Erlandsson on 2011-02-15.
Copyright (c) 2011 Procera Networks. All rights reserved.
"""

# TODO
# * Web update via MD5(ing) github and compare. Possibly through a thread.
# * dump/load NetObject tree states, including dynitems and tree in ASCII form
# * Add support for relative paths to cd


import atexit
import sys
import os
import pickle
import readline
import platform
import urllib
import md5
import difflib

import packetlogic2
from bash import Colors

CONNECTIONS_FILE = os.path.join(os.environ["HOME"], ".pyplcli_connections")
HISTORY_FILE     = os.path.join(os.environ["HOME"], ".pyplcli_history")

SCRIPT_URL = "https://github.com/emilerl/emilerl/raw/master/pyplcli/pyplcli.py"

connections = {}
c = Colors()
pl = None
rs = None
rt = None
cfg  = None
server = None
username = None
password = None
path = "/NetObjects"


#############################################################################
############################  "Shell commands" ##############################
#############################################################################

# command methods. As we don't know how many arguments the user will
# supply on the command line, each method must accept a variable length
# argument list (*args)

def update(*args):
    # TODO: Add support for ignoring configuration variables above.
    print c.white("Checking for an updated version...")
    print c.white("Retrieving %s..." % SCRIPT_URL),
    github_version = ""
    try:
        f = urllib.urlopen(SCRIPT_URL)
        github_version = f.read()
        f.close()
        print c.green("OK")
    except:
        print c.red("Failed!")
        return
    
    local_version = ""
    try:
        f = open(sys.argv[0], 'r')
        local_version = f.read()
        f.close()
    except:
        print c.error("Error: ") + c.white("Could not read local version %s" % sys.argv[0])
    
    github_md5 = md5.new(github_version).hexdigest()
    local_md5 = md5.new(local_version).hexdigest()
    if github_md5 != local_md5:
        print c.white("Local fingerprint:  ") + c.green(local_md5)
        print c.white("Github fingerprint: ") + c.red(github_md5)
        print c.white("Update available, downloading..."),
        prefix = sys.argv[0].split(".")[0]
        try:
            filename, headers = urllib.urlretrieve(SCRIPT_URL, prefix + "-%s.py" % github_md5)
            print c.green("OK")
            
            print c.white("Changes:")
            
            for line in difflib.context_diff(local_version.split("\n"), github_version.split("\n"), fromfile="Local Version", tofile="Github version"):
                if line.startswith("-"):
                    print c.red(line)
                elif line.startswith("!"):
                    print c.purple(line)
                elif line.startswith("+"):
                    print c.green(line)
                else:
                    print c.white(line)
            
            answer = raw_input("Do you want me to update this file (y/N)? ")
            if answer.lower() == "y":
                # TODO: implement automatic update...
                print c.red("Automatic update not yet implemented")
            else:
                print c.white("File downloaded to ./%s" % filename)
                print ""
                print c.red("Action required!")
                print c.white("The file has been downloaded, but you need to overwrite the current version.")
                print c.white("Overwrite this file by issuing the command (in your shell):")
                print c.yellow("  cp %s %s" % (filename, sys.argv[0]))
                print c.white("Optionally, make it executable by issuing the command:")
                print c.yellow("  chmod +x %s" % sys.argv[0])
                print ""
                print c.white("You can see what's been updated by issuing the command:")
                print c.yellow("  diff -Naur %s %s" % (sys.argv[0], filename))
        except:
            print c.red("Failed!")
        

def quit(*args):
    print c.white("Exiting...")
    disconnect()
    sys.exit(0)

def connect(*args):
    global pl, rs, rt, cfg, server, username, password
    if len(args[0]) < 3:
        print c.red("Error: ") + c.white("Not enough parameters")
        print c.green("Usage: ") + c.white("connect <host> <username> <password>")
    else:
        s = args[0][0]
        u = args[0][1]
        p = args[0][2]
        print c.white("Connecting to %s@%s...") % (u, s)
        try:
            if pl is not None:
                print c.yellow("Warning: ") + c.white("Connected to %s" % server)
                disconnect()
            
            pl = packetlogic2.connect(s, u, p)
            connections[server] = (u, p)
            rs = pl.Ruleset()
            rt = pl.Realtime()
            cfg = pl.Config()
            server = s
            username = u
            password = p
            print c.green("Connected!")
        except RuntimeError:
            print c.red("Failed")
            print c.white("Check your credentials or network connection") 

def ls(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        print c.white("Listing the contents of ") + c.green(path)
        objs = rs.object_list(path, recursive=False)
        for obj in objs:
            print obj.name

def cd(*args):
    global path
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        if args[0][0] == "..":
            path = os.path.dirname(path)
        else:
            tmp = " ".join(args[0])
            o = rs.object_get(os.path.join(path, tmp))
            if o is None:
                print c.red("Error: ") + c.white("No such path in NetObject tree: '%s'" % os.path.join(path, tmp))
            else:
                path = os.path.join(path, tmp)

def pwd(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        print c.white(path)

def history(*args):
    for i in range(readline.get_current_history_length()):
        print c.green("%d: " % i) + c.white(readline.get_history_item(i))

def hlp(*args):
    print c.yellow("Procera Networks Python CLI") + c.red(" v0.1") + "\n"
    print c.white("This is the interactive help\nHere is a list of all available commands\n")
    for key in sorted(functions.iterkeys()):
        print c.yellow(key)
        print "\t" + c.white(functions[key][1])
        print ""

def con(*args):
    global connections
    import pprint
    pprint.pprint(connections)

def config(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            key = args[0][0]
            items = cfg.list()
            found = False
            for i in items:
                if i["key"] == key:
                    print c.white("%s values:" % i["key"])
                    print c.green("* Default value:\t") + i["defvalue"]
                    print c.green("* Description:\t\t") + i["description"]
                    print c.green("* Max value:\t\t") + i["maxvalue"]
                    print c.green("* Min value:\t\t") + i["minvalue"]
                    print c.green("* Type\t\t\t") + str(i["type"])
                    print c.green("* Value:\t\t") + str(i["value"])
                    print c.green("* Visible:\t\t") + str(i["visible"])
                    found = True
                    break
                
            if not found:
                print c.red("Error: ") + c.white("No such config key")
        else:
            for i in cfg.list():
                print c.green(i["key"] + ": ") + c.white(str(i["value"]))

def disconnect(*args):
    global pl, rs, rt, cfg
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        print c.white("Disconnecting..."),
        pl = None
        rs = None
        rt = None
        cfg = None
        print c.green("OK")

def mono(*args):
    c.disable()
    
def color(*args):
    c.enable()
    
# Mapping between the text names and the python methods
# First item in list is a method handle and second is a help string used by the
# 'help' command.

functions = {
    'quit'          : [quit,    "Quit the program"],
    'exit'          : [quit,    "Quit the program"],
    'connect'       : [connect, "Connect to a server\n\tUsage: connect <hostname> <username> <password>"],
    'ls'            : [ls,      "List current path - just like the command you know and love"],
    'cd'            : [cd,      "Go to a specific path"],
    'pwd'           : [pwd,     'Print "working directory"'],
    'history'       : [history, 'Print command history'],
    'help'          : [hlp,     'This help message'],
    'connections'   : [con,     "List saved connections"],
    'config'        : [config,  "List configuration information for current connection"],
    'disconnect'    : [disconnect, "Disconnects from the current PacketLogic"],
    'mono'          : [mono,    "Turn off color support"],
    'color'         : [color,   "Turn on color support"],
    'update'        : [update,  "Update pyplcli.py to the latest version from github.com"],
}

#############################################################################
############################  End of commands ###############################
#############################################################################

def tc(text, state):
    print "text: %s" % text
    print "state: %d" % state
    print c.red("Working on Tab completion")
    return None

def save_connections():
    print c.white("Saving connection information..."),
    try:
        output = open(CONNECTIONS_FILE, 'wb')
        pickle.dump(connections, output)
        output.close()
        print c.green("OK")
    except IOError:
        print c.red("Failed")

def dispatch(line):
    parts = line.split()
    if len(parts) is 0:
        return
        
    if not parts[0] in functions:
        print c.red("Unknown command '%s'" % parts[0])
    else:
        functions[parts[0]][0](parts[1:])

def prompt():
    count = 0
    while True:
        try:
            if pl is not None:
                #line = raw_input(c.blue(">> [%d]" % count) + " (%s): " % path)
                line = raw_input(c.blue(">> [%d]" % count) + c.red(" (%s@%s)" % (username, server)) + c.yellow(" (%s): " % path))
            else:
                line = raw_input(c.blue(">> [%d]: " % count) + c.red("(disconnected): "))
            print ""
            dispatch(line)
            count = count + 1
        except KeyboardInterrupt, EOFError:
            quit()

def main():
    global c, connections
    print c.yellow("Procera Networks Python CLI") + c.red(" v0.1") + "\n"
    print c.white("Welcome to the interactive console")
    print c.white("To get a list of commands, type help\n")
    print c.white("Initializing...")
    
    # Initialize readline
    try:
        print c.white("Reading command history..."),
        if os.path.exists(HISTORY_FILE):
            readline.read_history_file(HISTORY_FILE)
            print c.green("OK")
        else:
            print c.green("No history found")
    except IOError:
        print c.red("Error: ") + "Could not read history file '%s'" % HISTORY_FILE
        sys.exit(1) 
    
    if platform.system() == 'Darwin':
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind('tab: complete')
    readline.set_completer(tc)
    
    print c.white("Loading connection data... "),
    if os.path.exists(CONNECTIONS_FILE):
        print c.green("OK")
        con_data = open(CONNECTIONS_FILE, 'rb')
        connections = pickle.load(con_data)
    else:
        print c.green("No connections found")
    
    atexit.register(readline.write_history_file, HISTORY_FILE)
    atexit.register(save_connections)
    
    print ""
    prompt()

if __name__ == '__main__':
    main()

