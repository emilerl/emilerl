#!/usr/bin/env python
# encoding: utf-8

"""
pyplcli.py

Created by Emil Erlandsson <eerlandsson@proceranetworks.com>
Copyright (c) 2011 Emil Erlandsson. All rights reserved.

The pyplcli is a PacketLogic command line interface, mainly developed for 
manipulating the NetObject tree using a shell like interface (ls, cd, mkdir etc).
It can also read configuration data, add- or remove dynamic items, dump- and load
a current NetObject structure.

USAGE:
  python pyplcli.py
  
UPDATE:
  The script can update itself. Just issue the 'update' command in the shell and
  follow the instructions.
  
"""

# TODO
# * dump/load NetObject tree states, including dynitems and tree in ASCII form
# * Add support for relative paths to cd
# * Clean up code for ls, lsl and tree
# * Fix autocomlpete
# * add support for adding port and other objects

CHANGELOG = {
    "0.1":     "All features added",
    "0.2":     "Added support for scripting",
    "0.3":     "Added support for arguments parsing",
    "0.9.1":   "Bumped version number as we are getting closer to 1.0",
    "0.9.2":   "Stability updates. Also fixed the 13.1 problem.",
    "0.9.3":   "Added bookmarks and aliases",
    "0.9.4":   "Polishing and stability tweaks",
    "0.9.5":   "Added support for exporting a tree (exporttree). Still a bit dodgy.",
    "0.9.6":   "Support for plugins added. Fixed 'top' command.",
    "0.9.7":   "Added support for piping output and grep and igrep commands",
}
SCRIPT_VERSION = sorted(CHANGELOG.iterkeys(), reverse=True)[0]

import atexit
import sys
import os
import pickle
import readline
import platform
import urllib
import hashlib
import difflib
import shutil
import curses
import urllib
import subprocess
import getopt
import socket
import imp
import traceback
import re
from operator import attrgetter

try:
    import packetlogic2
except:
    print "PacketLogic Python API required for this script to run."
    print "Go to http://download.proceranetworks.com and download the correct"
    print "version for your machine."
    sys.exit(1)


PICKLE_FILE     = os.path.join(os.environ["HOME"], ".pyplcli.pickle")
HISTORY_FILE    = os.path.join(os.environ["HOME"], ".pyplcli_history")
MACRO_DIR       = os.path.join(os.environ["HOME"], ".pyplcli_macros")
SCRIPT_URL      = "https://github.com/emilerl/emilerl/raw/master/pyplcli/pyplcli.py"


# Bash utility functions
RESET = '\001\033[0m\002'
CCODES = {
    'black'           :'\001\033[0;30m\002',
    'blue'            :'\001\033[0;34m\002',
    'green'           :'\001\033[0;32m\002',
    'cyan'            :'\001\033[0;36m\002',
    'red'             :'\001\033[0;31m\002',
    'purple'          :'\001\033[0;35m\002',
    'brown'           :'\001\033[0;33m\002',
    'light_gray'      :'\001\033[0;37m\002',
    'dark_gray'       :'\001\033[0;30m\002',
    'light_blue'      :'\001\033[0;34m\002',
    'light_green'     :'\001\033[0;32m\002',
    'light_cyan'      :'\001\033[0;36m\002',
    'light_red'       :'\001\033[0;31m\002',
    'light_purple'    :'\001\033[0;35m\002',
    'yellow'          :'\001\033[0;33m\002',
    'white'           :'\001\033[0;37m\002',
    'redbg'           :'\001\033[41m\002'  ,  
}

MCODES = {
    'POS_LC'            : '\001\033[%d;%df\002',
    'MOVE_UP_N'         : '\001\033[%dA\002'   ,
    'MOVE_DOWN_N'       : '\001\033[%dB\002'   ,
    'MOVE_FORWARD_N'    : '\001\033[%dC\002'   ,
    'MOVE_BACK_N'       : '\001\033[%dD\002'   ,
    'CLEAR'             : '\001\033[2J\033[H\002'    ,
    'ERASE_EOL'         : '\001\033[K\002'     ,
    'SAVE'              : '\001\033[s\002'     ,
    'RESTORE'           : '\001\033[u\002'     , 
}

def terminal_size():
    import fcntl, termios, struct
    try:
        h, w, hp, wp = struct.unpack('HHHH',
            fcntl.ioctl(0, termios.TIOCGWINSZ,
            struct.pack('HHHH', 0, 0, 0, 0)))
    except IOError:
        return 0,0
    return w, h

class Screen(object):
    """Helper class for moving the cursor on the screen"""
    
    def __init__(self):
        curses.setupterm()
        self.clear_str = curses.tigetstr("clear")
        
    def save_position(self):
        print MCODES["SAVE"],
    
    def restore_position(self):
        print MCODES["RESTORE"],
        
    def move_up(self,lines = 1):
        print MCODES["MOVE_UP_N"] % lines,
    
    def move_down(self, lines = 1):
        print MCODES["MOVE_DOWN_N"] % lines,
        
    def move_forward(self, cols = 1):
        print MCODES["MOVE_FORWARD_N"] % cols,

    def move_backward(self, cols = 1):
        print MCODES["MOVE_BACK_N"] % cols,
    
    def position(self, x, y):
        "x=line, y=column"
        print MCODES["POS_LC"] % (x,y)
    
    def clear(self):
        print '\001' + self.clear_str + '\002'
            
    def erase_line(self):
        print MCODES["ERASE_EOL"],

class Colors(object):
    """A helper class to colorize strings"""
    def __init__(self, state = False, quiet = False):
        self.disabled = state
        self.quiet = quiet
    
    def disable(self):
        self.disabled = True
        
    def enable(self):
        self.disabled = False
        
    def be_quiet(self):
        self.quiet = True
    
    def verbose(self):
        self.quiet = False
            
    def __getattr__(self,key):
        if self.quiet:
            return lambda x: ""
        if key not in CCODES.keys():
            raise AttributeError, "Colors object has no attribute '%s'" % key
        else:
            if self.disabled:
                return lambda x: x
            else:
                return lambda x: RESET + CCODES[key] + x + RESET 
    
    def __dir__(self):
        return self.__class__.__dict__.keys() + CCODES.keys()

    def error(self, message):
        if self.disabled:
            return message
        else:
            return CCODES["redbg"] + message + RESET
                    
# EO: Bash utility functions

connections = {}
macros = {}
bookmarks = {}
aliases = {}
macro_buffer = []
macro_record = False
current_macro = ""
simpleprompt = False
plugins = {}
c = Colors()
s = Screen()
pl = None
rs = None
rt = None
cfg  = None
server = None
username = None
password = None
path = "/NetObjects"
output_buffer = []
buffer_output = False


#############################################################################
############################  "Shell commands" ##############################
#############################################################################

# command methods. As we don't know how many arguments the user will
# supply on the command line, each method must accept a variable length
# argument list (*args)


def not_implemented(*args):
    error("This command is not implemented yet.")
    iprint(c.green("Tip: ") + c.white("Try the 'update' command to see if there is a new version of the script."))

def update(*args):
    iprint(c.white("Checking for an updated version..."))
    iprint(c.white("Retrieving %s..." % SCRIPT_URL),newline=False)
    github_version = ""
    try:
        f = urllib.urlopen(SCRIPT_URL)
        github_version = f.read()
        f.close()
        iprint(c.green("OK"))
    except:
        iprint(c.red("Failed!"))
        return
    
    local_version = ""
    try:
        f = open(sys.argv[0], 'r')
        local_version = f.read()
        f.close()
    except:
        error("Could not read local version %s" % sys.argv[0])
    
    github_md5 = hashlib.md5(github_version).hexdigest()
    local_md5 = hashlib.md5(local_version).hexdigest()
    if github_md5 != local_md5:
        iprint(c.white("Local fingerprint:  ") + c.green(local_md5))
        iprint(c.white("Github fingerprint: ") + c.red(github_md5))
        iprint(c.white("Update available, downloading..."),newline=False)
        prefix = sys.argv[0].split(".")[0]
        try:
            filename, headers = urllib.urlretrieve(SCRIPT_URL, prefix + "-%s.py" % github_md5)
            iprint(c.green("OK"))
            iprint(c.white("Changes:"))
            
            for line in difflib.context_diff(local_version.split("\n"), github_version.split("\n"), fromfile="Local Version", tofile="Github version"):
                if line.startswith("-"):
                    iprint(c.red(line))
                elif line.startswith("!"):
                    iprint(c.purple(line))
                elif line.startswith("+"):
                    iprint(c.green(line))
                else:
                    iprint(c.white(line))
            
            answer = raw_input("Do you want me to update this file (y/N)? ")
            if answer.lower() == "y":
                backup_file = sys.argv[0].split(".")[0] + "-backup.py"
                iprint(c.white("Creating backup file ") + c.green(sys.argv[0].split(".")[0]))
                try:
                    shutil.copyfile(sys.argv[0], backup_file)
                    f = open(sys.argv[0], "w")
                    f.write(github_version)
                    f.close()
                    
                    iprint(c.green("File updated!"))
                    iprint(c.white("Removing temporary update file %s" % prefix + "-%s.py..." % github_md5),newline=False)
                    try:
                        os.remove(prefix + "-%s.py" % github_md5)
                        iprint(c.green("OK"))
                    except:
                        iprint(c.red("Failed"))
                    iprint(c.white("Restart pyplcli for the changes to have effect."))
                    # Todo: Relaunch does not work.
                    #sys.stdout.flush()
                    #disconnect()
                    #save_state()
                    #subprocess.Popen(["/usr/bin/env","python",os.path.join(os.getcwd(),sys.argv[0])])
                except:
                    error("Could not update automatic. Run manual update")
            else:
                iprint(c.white("File downloaded to ./%s" % filename))
                iprint("")
                iprint(c.red("Action required!"))
                iprint(c.white("The file has been downloaded, but you need to overwrite the current version."))
                iprint(c.white("Overwrite this file by issuing the command (in your shell):"))
                iprint(c.yellow("  cp %s %s" % (filename, sys.argv[0])))
                iprint(c.white("Optionally, make it executable by issuing the command:"))
                iprint(c.yellow("  chmod +x %s" % sys.argv[0]))
                iprint("")
                iprint(c.white("You can see what's been updated by issuing the command:"))
                iprint(c.yellow("  diff -Naur %s %s" % (sys.argv[0], filename)))
        except:
            iprint(c.red("Failed!"))
    else:
        iprint(c.white("Local fingerprint:  ") + c.green(local_md5))
        iprint(c.white("Github fingerprint: ") + c.green(github_md5))
        iprint(c.white("No new update on github"))
        

def quit(*args):
    iprint(c.white("Exiting..."))
    disconnect()
    update_plugins("quit", "pyplcli.py exiting.")
    sys.exit(0)

def connect(*args):
    global pl, rs, rt, cfg, server, username, password, connections
    s = ""
    u = ""
    p = ""
    if len(args[0]) == 1:
        s = args[0][0]
        if connections.has_key(s):
            
            u = connections[s][0]
            p = connections[s][1]
        else:
            error("No such connection %s" % s)
            return 
    elif len(args[0]) < 3:
        error("Not enough parameters")
        iprint(c.green("Usage: ") + c.white("connect <host> <username> <password>"))
        return
    else:
        s = args[0][0]
        u = args[0][1]
        p = args[0][2]
    
    iprint(c.white("Connecting to %s@%s...") % (u, s))
    try:
        if pl is not None:
            warning("Connected to %s" % server)
            disconnect()
        
        pl = packetlogic2.connect(s, u, p)
        connections[s] = (u, p)
        rs = pl.Ruleset()
        rt = pl.Realtime()
        cfg = pl.Config()
        server = s
        username = u
        password = p
        iprint(c.green("Connected!"))
        update_plugins("connect", "Connected.")
    except RuntimeError, e:
        #error("Check your credentials or network connection")
        update_plugins("connect", "Connect failed: %s" % str(e))
        error(str(e))
        if str(e).startswith("Could not determine server version"):
            iprint(c.white("Your installed PacketLogic Python API does not match the FW version in the PRE."))
            iprint(c.white("Locally supported APIs:"))
            for v in packetlogic2._available_apis():
                iprint(c.green(" * %s" % v.replace("_",".")))
    except socket.error:
        error("Socket IO error trying to connect to %s" % s)
        update_plugins("connect", "Connect failed: socket error.")

def reconnect():
    global pl, rs, rt, cfg
    disconnect()
    iprint(c.white("Re-connecting..."),newline=False)
    try:
        pl = packetlogic2.connect(server, username, password)
        rs = pl.Ruleset()
        rt = pl.Realtime()
        cfg = pl.Config()
        update_plugins("connect", "Reconnected.")
        iprint(c.green("Ok"))
    except RuntimeError:
        iprint(c.red("Failed"))
        iprint(c.white("Check your credentials or network connection"))
        update_plugins("connect", "Re-connect failed.") 

def dynrm(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            ipregex = "[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}"
            dynitems = rt.dyn_list_full()
            toremove = []
            
            if args[0][0] == "all" or args[0][0] == "*":
                iprint(c.white("Removing ") + c.red("_ALL_ ") + c.white("dynitems!"))
                resp = raw_input(c.red("Are you sure you want to continue") + c.white(" (y/N)? : "))
                if resp == "y":
                    for noid,ip,sub in dynitems:
                        toremove.append((noid, ip, sub))
            elif args[0][0] == "lingering":
                iprint("Removing dynitems with no parent")
                for noid, ip, sub in dynitems:
                    no = rs.object_find_id('/NetObjects', noid)
                    if no is None:
                        toremove.append((noid, ip, sub))
            elif re.match(ipregex, args[0][0]) is not None:
                for noid, ip, sub in dynitems:
                    if ip == args[0][0]:
                        toremove.append((noid, ip, sub))
            else:
                subscriber = args[0][0]                
                for noid, ip, sub in dynitems:
                    if sub == subscriber:
                        toremove.append((noid, ip, sub))

            for noid, ip, sub in toremove:
                iprint("Removing: %s (%s, %s)" % (str(sub), str(ip), str(noid)))
                rt.dyn_remove(noid, ip)
        else:
            usage_error("dynrm")

def dynadd(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            ip = args[0][0]
            subscriber = None
            if len(args[0]) >= 2:
                subscriber = " ".join(args[0][1:])
            o = rs.object_find(path)
            if o is not None:
                iprint(c.white("Adding") + c.green(" (%s, %s)" % (ip, subscriber)) + c.white(" to ") + c.red(path))
                rt.dyn_add(o.id, ip, subscriber)
            else:
                error("Cannot add dynitems in %s" % path)
        else:
            usage_error("dynadd")
            
def dynlist(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        dynitems = rt.dyn_list_full()
        if len(args[0]) > 0:
            if args[0][0] == "all":
                iprint(c.white("Listing all the dynamic items"))
                for noid,ip,sub in dynitems:
                    no = rs.object_find_id('/NetObjects', noid)
                    if no is not None:
                        iprint(c.white(os.path.join(no.path, no.name) + "/") + c.light_green(ip) + " " + c.red("(%s)" % sub))
                    else:
                        iprint(c.red("Lingering: ") + c.light_green(ip) + " " + c.red("(%s)" % sub))
            else:
                iprint(c.red("Error:") + c.white(" '%s' is not a valid flag for dynlist" % args[0][0]))
        else:
            iprint(c.white("Listing the dynamic items of ") + c.green(path))
            
            for noid, ip, sub in dynitems:
                no = rs.object_find_id(path, noid)
                if no is not None:
                    if os.path.join(no.path, no.name) == path:
                        iprint(c.white(os.path.join(no.path, no.name) + "/") + c.light_green(ip) + " " + c.red("(%s)" % sub))

def ls(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        tmp_path = path
        if len(args[0]) > 0:
            tmp_path = os.path.join(path, args[0][0])
        iprint(c.white("Listing the contents of ") + c.green(tmp_path))
        objs = rs.object_list(tmp_path, recursive=False)
        for obj in sorted(objs, key=lambda o: o.name):
            iprint(c.blue(obj.name))
        o = rs.object_find(tmp_path)
        if o is not None:
            for i in o.items:
                extra = "" if i.value2 == "" else "/" + c.purple(str(i.value2))
                iprint(c.purple(str(i.value1)) + extra)

def tree(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        iprint(c.white("Listing the contents of ") + c.green(path))
        objs = rs.object_list(path, recursive=True)
        objs = sorted(objs, key=attrgetter("path"))
        for obj in objs:
            iprint(c.green(obj.path) + "/" +c.blue(obj.name))
            if obj is not None:
                for i in obj.items:
                    iprint(c.green(obj.path) + "/" +c.purple(i.value1) + "/" + c.purple(i.value2))

def lsl(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        tmp_path = path
        if len(args[0]) > 0:
            tmp_path = os.path.join(path, args[0][0])
        iprint(c.white("Listing the contents of ") + c.green(tmp_path))
        objs = rs.object_list(tmp_path, recursive=False)
        for obj in objs:
            iprint(c.white("%8d" % obj.id + "  " + str(obj.type) + "  " + str(obj.creation_date) + "  " + str(obj.modification_date) + "  " + c.yellow(str(obj.creator)) + "  ") + c.blue(obj.name))
        o = rs.object_find(path)
        if o is not None:
            for i in o.items:
                iprint(c.white("%8d" % i.id + "  " + str(i.type) + "  " + str(i.creation_date) + "  " + str(i.modification_date) + "  " + c.yellow(str(i.creator)) + "  ") + c.purple(i.value1) + "/" + c.purple(i.value2))
        

def cd(*args):
    global path
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        if len(args[0]) == 0:
            path = "/NetObjects"
        elif args[0][0] == "..":
            if path != "/NetObjects":
                path = os.path.dirname(path)
        else:
            tmp = " ".join(args[0])
            if tmp == "/":
                path = "/NetObjects"
                return
            else:
                tmp = os.path.join(path, tmp)
                
            o = rs.object_find(tmp)
            iprint(tmp)
            if o is None:
                error("No such path in NetObject tree: '%s'" % tmp)
            else:
                path = tmp

def pwd(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        iprint(c.white(path))

def mkdir(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            no_name = " ".join(args[0])
            parts = no_name.split("/")
            cpwd = path
            for part in parts:
                what = os.path.join(cpwd, part)
                o = rs.object_find(what)
                if o is None:
                    oid = rs.add(what)
                    iprint(c.white("New object '%s' with id: %d" % (what, oid)))
                else:
                    warning("NetObject %s already exists! Skipping" % what)
                cpwd = what
            rs.commit()
            iprint(c.white("Created NetObject path: ") + c.green("%s" % cpwd))
        else:
            error("Usage: mkdir name")

def remove(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            no_name = " ".join(args[0])
            what = os.path.join(path, no_name)
            o = rs.object_find(what)
            if o is not None:
                iprint(c.white("Deleting NetObject path: ") + c.green("%s" % what))
                rs.object_remove(what)
                resp = raw_input(c.red("Are you sure you want to continue") + c.white(" (y/N)? : "))
                if resp == 'y':
                    rs.commit()
                else:
                    rs.rollback()
            else:
                error("No such NetObject '%s'" % what)
        else:
            error("Usage: mkdir name")

def history(*args):
    filter = ""
    if len(args[0]) == 1:
        filter = args[0][0]
    try:
        myscreen = curses.initscr()
        height = myscreen.getmaxyx()[0] - 1
        myscreen.clear()
        curses.endwin()
        s.clear()
        counter = 0

        for i in range(1, readline.get_current_history_length()):
            if counter == height:
                raw_input(c.blue("[%.0f %%] " % float(float(i) / float(readline.get_current_history_length())* 100)  ) +c.yellow("Press RETURN to continue (or CTRL-c to cancel) "))
                s.clear()
                counter = 0
            item = readline.get_history_item(i)
            if item.startswith(filter):
                iprint(c.green(" %04d :  " % i) + c.white(str(item)))
                counter += 1
    except:
        s.clear()

def hlp(*args):
    if len(args[0]) > 0:
        command = args[0][0]
        if command in functions.keys():
            iprint(c.yellow(command))
            iprint("\t" + c.white(functions[command][1]))
        else:
            iprint(c.red("Unknown command '%s'" % command))
            iprint(c.green("Tip: ") + c.white("Try 'help' for a list of commands"))
    else:
        s.clear()
        iprint(c.yellow("Procera Networks Python CLI") + c.red(" v%s" % SCRIPT_VERSION) + "\n")
        iprint(c.white("This is the interactive help\nHere is a list of all available commands\n"))
        iprint()
        iprint(c.green("Tip of the day!"))
        iprint(c.white("\tOutput from all commands can be piped to grep or igrep using |"))
        iprint()
        
        for key in sorted(functions.iterkeys()):
            iprint(c.yellow(key))
        iprint(c.white("\nUse 'help <command>' for more information on each command"))

def con(*args):
    ping = False
    if len(args[0]) == 1:
        if args[0][0] == "status":
            ping = True
    
    print
    iprint(c.white("Saved PacketLogic connections:"))
    for packetlogic, values in connections.iteritems():
        if ping:
            online = True
            try:
                pl = packetlogic2.connect(packetlogic, values[0], values[1])
            except RuntimeError:
                online = False
            except socket.error:
                online = False
            status = c.green("[ONLINE]")
            if not online:
                status = c.red("[OFFLINE]")
                
            iprint(status + c.white(" ") + c.blue(values[0]) + c.white(":") + c.blue(values[1]) + c.white("@") + c.yellow(packetlogic))
        else:
            iprint(c.white(" * ") + c.blue(values[0]) + c.white(":") + c.blue(values[1]) + c.white("@") + c.yellow(packetlogic))
    print
    
def config(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            key = args[0][0]
            items = cfg.list()
            found = False
            for i in items:
                if i["key"] == key:
                    iprint(c.white("%s values:" % i["key"]))
                    iprint(c.green("* Default value:\t") + i["defvalue"])
                    iprint(c.green("* Description:\t\t") + i["description"])
                    iprint(c.green("* Max value:\t\t") + i["maxvalue"])
                    iprint(c.green("* Min value:\t\t") + i["minvalue"])
                    iprint(c.green("* Type\t\t\t") + str(i["type"]))
                    iprint(c.green("* Value:\t\t") + str(i["value"]))
                    iprint(c.green("* Visible:\t\t") + str(i["visible"]))
                    found = True
                    break
                
            if not found:
                error("No such config key")
                items = [i["key"] for i in items if i["key"].startswith(key)]
                iprint(c.green("Tip: " + c.white("Possible matches are %s" % str(items))))
        else:
            for i in cfg.list():
                iprint(c.green(i["key"] + ": ") + c.white(str(i["value"])))

def disconnect(*args):
    global pl, rs, rt, cfg
    iprint(c.white("Disconnecting..."),newline=False)
    pl = None
    rs = None
    rt = None
    cfg = None
    iprint(c.green("OK"))
    update_plugins("connect", "Disconnected")

def mono(*args):
    global c
    iprint(c.white("Turning color support off. Turn on again with command 'color'"))
    c.disable()
    
def color(*args):
    global c
    iprint(c.white("Turning color support on. Turn off again with command 'mono'"))
    c.enable()
    print
    iprint(c.purple("C") + c.red("O") + c.yellow("L") + c.green("O") + c.cyan("R") + c.blue("S") + " " + c.white("enabled. Fun huh?"))
    print
    
def record(*args):
    global macro_record, current_macro
    if not macro_record:
        if len(args[0]) != 1:
            usage_error("record")
        else:
            current_macro = args[0][0]
            if macros.has_key(current_macro):
                warning("Macro %s exists. All commands will be appended" % current_macro)
            macro_record = True
            iprint(c.green("Macro recording started..."))
    else:
        error("Already recording. Don't worry though, this comman will not be recorded")
    
def stop(*args):
    global macro_record, current_macro
    if macro_record:
        macro_record = False
        current_macro = ""
        iprint(c.red("Macro recording stopped..."))
    else:
        error("Not recording at the moment")

def list_macro(*args):
    global macro_record, macros
    if len(args[0]) == 0:
        for macro in macros.keys():
            iprint(c.yellow(macro))
    elif len(args[0]) == 1:
        if macros.has_key(args[0][0]):
            for command in macros[args[0][0]]:
                iprint(c.purple(" ".join(command)))
    else:
        iprint(c.red("No recorded macros"))

def play(*args):
    if len(args[0]) == 1:
        if macros.has_key(args[0][0]):
            for command in macros[args[0][0]]:
                if not command[0].startswith("#"):
                    iprint(c.green("Executing: ") + c.white(" ".join(command)))
                    functions[str(command[0])][0](command[1:])
    else:
        usage_error("play")
    
def rmmacro(*args):
    global macros
    if len(args[0]) == 1:
        if macros.has_key(args[0][0]):
            del macros[args[0][0]]

def liveview(*args):
    global rt, pl
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        def lvupdate(data):
            import time
            myscreen = curses.initscr()
            myscreen.clear()
            myscreen.border(0)
            if not c.disabled:
                curses.start_color()
            
                curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
                curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
                curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
                curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_BLACK)
            ts = time.strftime("[ %Y-%m-%d %H:%M:%S ]")
            if not c.disabled:    
                myscreen.addstr(0, 2, "[ %s ]" % path, curses.color_pair(1))
                myscreen.addstr(0, myscreen.getmaxyx()[1] - (len("[ CTRL+c to exit ]") + 2), "[ CTRL+c to exit ]", curses.color_pair(4))
                myscreen.addstr(myscreen.getmaxyx()[0]-1 , myscreen.getmaxyx()[1] - (len(ts) + 2) , ts, curses.color_pair(1))
            else:
                myscreen.addstr(0, 2, "[ %s ]" % path)
                myscreen.addstr(0, myscreen.getmaxyx()[1] - (len("[ CTRL+c to exit ]") + 2), "[ CTRL+c to exit ]")
                myscreen.addstr(myscreen.getmaxyx()[0]-1 , myscreen.getmaxyx()[1] - (len(ts) + 2) , ts)
            counter = 3
            total = 0
            for m in data:
                if not counter > myscreen.getmaxyx()[0] - 2:
                    total += m.speed[0]*8.0/1000 + m.speed[1]*8.0/1000
            
            if not c.disabled:        
                myscreen.addstr(1, 2, "NetObject" + (50 - len("NetObject")) * " " + "In (Kbps)" + (15 - len("In (Kbps)")) * " " + "Out (Kbps)" + (15 - len("Out (Kbps)")) * " " + "Percent of total" , curses.color_pair(2))
            else:
                myscreen.addstr(1, 2, "NetObject" + (50 - len("NetObject")) * " " + "In (Kbps)" + (15 - len("In (Kbps)")) * " " + "Out (Kbps)" + (15 - len("Out (Kbps)")) * " " + "Percent of total")
            myscreen.hline(2,1, "-", myscreen.getmaxyx()[1] - 2)
            counter = 3

            try:
                data.sort(key=lambda no: no.speed[0] + no.speed[1])
                data.reverse()
            except AttributeError:
                pass # At least we tried

            for m in data:
                if not counter > myscreen.getmaxyx()[0] - 2:
                    ratio = float(0)
                    if total != 0:
                        ratio = float((m.speed[0]*8.0/1000 + m.speed[1]*8.0/1000) / total)
                    ins = str(m.speed[0]*8.0/1000)
                    outs = str(m.speed[1]*8.0/1000)
                    if not c.disabled:  
                        myscreen.addstr(counter, 2, m.name + (50 - len(m.name)) * " " + ins + (15 - len(ins)) * " " + outs + (15 - len(outs)) * " " + "%0.1f" % (ratio *100), curses.color_pair(3) )
                    else:
                        myscreen.addstr(counter, 2, m.name + (50 - len(m.name)) * " " + ins + (15 - len(ins)) * " " + outs + (15 - len(outs)) * " " + "%0.1f" % (ratio *100))
                    counter +=1
                    
            myscreen.refresh()
            curses.flash()

        if path == "/NetObjects":
            rt.add_netobj_callback(lvupdate)
        else:
            rt.add_netobj_callback(lvupdate, under=path)

        try:
            rt.update_forever()
        except:
            pass
            # Not compatible with 13.1
            # rt.stop_updating()

        curses.endwin()
        s.clear()
        reconnect()
               
def clear(*args):
    s.clear()
    
def top(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        class ProgressBar(object):
            def __init__(self, name="", width=40, initvalue=0):
                self.width = width
                self.name=name
                self.value = int(initvalue)
        
            def render(self):
                s = " %d %% " % self.value
                filled = int(float(float(self.value) / 100.00) * (self.width - 2))
                non_filled = int(self.width - 2 - filled)
                iprint(c.green("%-20s" % self.name) + " " + c.yellow("[") + ("#" * filled) + (" " * non_filled) + c.yellow("]") + c.red("  %s" %s))
                
        data = rt.get_sysdiag_data()
        width, height = terminal_size()
        wrap = int(width * 0.4)
        print
        p = ProgressBar(" * Memory usage", wrap, data["General"]["Memory used"]["value"]).render()
        print
        p = ProgressBar(" * CPU(0) usage", wrap, data["General"]["CPU Usage (0)"]["value"]).render()
        p = ProgressBar(" * CPU(1) usage", wrap, data["General"]["CPU Usage (1)"]["value"]).render()
        print
        p = ProgressBar(" * CPU(0) User", wrap, data["General"]["CPU User (0)"]["value"]).render()
        p = ProgressBar(" * CPU(1) User", wrap, data["General"]["CPU User (1)"]["value"]).render()
        print
        p = ProgressBar(" * CPU(0) System", wrap, data["General"]["CPU System (0)"]["value"]).render()
        p = ProgressBar(" * CPU(1) System", wrap, data["General"]["CPU System (1)"]["value"]).render()
        print
        p = ProgressBar(" * CPU(0) Nice", wrap, data["General"]["CPU Nice (0)"]["value"]).render()
        p = ProgressBar(" * CPU(1) Nice", wrap, data["General"]["CPU Nice (1)"]["value"]).render()
        print

def visible(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        o = rs.object_find(path)
        if o is not None:
            if o.visible:
                iprint(c.white("NetObject ") + c.green("%s" % path) + c.white(" is visible. Setting visible to false."))
            else:
                iprint(c.white("NetObject ") + c.green("%s" % path) + c.white(" is not visible. Setting visible to true."))
            o.set_visible(not o.visible)
            rs.commit()
        else:
            error("cannot toggle visibility for %s" % path)

def portobject(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        cmds = ["list", "add", "remove"]
        if len(args[0]) > 0:
            cmd = args[0][0]
            if cmd == "list":
                objs = rs.object_list('/PortObjects')
                for obj in objs:
                    iprint(c.light_green(os.path.join("/PortObjects", obj.name)))
                    for i in obj.items:
                        iprint(" * ITEM: %s" % i)
        else:
            usage_error("portobject")

def add_item(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            item = args[0][0]
            iprint(c.white("Adding: ") + c.green("%s" % item) + c.white(" to ") + c.red(path))
            o = rs.object_find(path)
            if o is not None:
                o.add(item)
                rs.commit()
            else:
                error("Can not add item here: %s" % path)
        else:
            usage_error("add")

def del_item(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            item = args[0][0]
            
            o = rs.object_find(path)
            if o is not None:
                item = item.replace("/", "-") if "/" in item else item
                if item in o.items:
                    iprint(c.white("Removing: ") + c.green("%s" % item) + c.white(" from ") + c.red(path))
                    o.remove(item)
                else:
                    error("No such item '%s'" % item)
                rs.commit()
            else:
                error("Can not remove item here: %s" % path)
        else:
            usage_error("del")

def version(*args):
    iprint(c.white("Current software version is: v%s" % SCRIPT_VERSION))
    print
    iprint(c.white("Changelog (5 latest versions)"))
    count = 0
    for key in sorted(CHANGELOG.iterkeys(), reverse=True):
        if count == 4:
            break
        iprint("* " + c.red(key))
        iprint("\t" + c.yellow(CHANGELOG[key]))
        count += 1
    print
    iprint(c.white("Configuration variables:"))
    iprint(c.red("Data file: ") + c.yellow(PICKLE_FILE))
    iprint(c.red("History file: ") + c.yellow(HISTORY_FILE))
    iprint(c.red("Script directory: ") + c.yellow(MACRO_DIR))
    
    
def hosts(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        maxhosts = 500
        if len(args[0]) > 0:
            maxhosts = int(args[0][0])
            
        hostlist = []
        def cb(data):
            iprint(c.white("Update received.") + c.red(" %d" % len(hostlist)) + c.white(" entries in host list.") + c.yellow(" Press CTRL+c to cancel capture."))
            if len(hostlist) > maxhosts:
                raise Exception
            for host in data.hosts:
                hostlist.append(host.addr)
        rt.add_netobj_callback(cb, under="/NetObjects/<Ungrouped>", include_hosts=True)
        try:
            rt.update_forever()
        except:
            pass
            # Not compatible with 13.1
            # rt.stop_updating()
        
        hostlist = hostlist[:maxhosts]
        
        myscreen = curses.initscr()
        height = myscreen.getmaxyx()[0] - 1
        myscreen.clear()
        curses.endwin()
        s.clear()
        counter = 0
        for x in hostlist:
            if counter == height:
                raw_input(c.yellow("Press RETURN to continue"))
                s.clear()
                counter = 0
            iprint(c.green(x))
            counter += 1
            
        reconnect()
        
def runscript(*args):
    if len(args[0]) == 1:
        scriptfile = args[0][0]
        if not os.path.exists(scriptfile):
            error("Script file '%s' does not exist." % scriptfile)
            return
            
        run_script(scriptfile, exit_after=False)
    else:
        usage_error("run")
    
def editscript(*args):
    if len(args[0]) == 1:
        scriptfile = args[0][0]
        reload = False
        if scriptfile in macros.keys():
            scriptfile = os.path.join(MACRO_DIR, scriptfile + ".pli")
            reload = True
        
        if not os.path.exists(scriptfile):
            warning("Script file '%s' does not exist." % scriptfile)
            resp = raw_input(c.white("Do you want me to create it for you? (Y/n): "))
            if resp.lower() == "n":
                return
            else:
                f = open(scriptfile, 'w')
                f.write('')
                f.close()
        
        editor = None
        if os.environ.has_key("EDITOR"):
            editor =  os.environ["EDITOR"]
        else:
            editor = "/usr/bin/nano -w"
        
        subprocess.call(editor + " %s" % scriptfile, shell=True)
        
        if reload:
            load_script(scriptfile)        
    else:
        usage_error("edit")

def alias(*args):
    global aliases
    if len(args[0]) == 0:
        for key in aliases.iterkeys():
            iprint(c.green(key) + c.blue(" -> ") + c.red(aliases[key]))
    elif len(args[0]) > 1:
        name = args[0][0]
        
        if name in functions.iterkeys():
            error("You can not use existing command names for alias names")
            return
        
        if aliases.has_key(name):
            warning("Replacing alias %s" % name)
        
        aliases[name] = " ".join(args[0][1:])
        iprint(c.white("Recorded alias '") + c.red(name) + c.white("' as '") + c.blue(aliases[name]) + c.white("'") )
    else:
        usage_error("alias")
        
        
def rmalias(*args):
    global aliases
    if len(args[0]) == 1:
        if aliases.has_key(args[0][0]):
            iprint(c.white("Removing alias: %s" % args[0][0]))
            del aliases[args[0][0]]
        else:
            error("No such alias: %s" % args[0][0])
    else:
        usage_error("rmalias")

def rmbookmark(*args):
    global bookmarks
    if len(args[0]) == 1:
        name = args[0][0]
        if bookmarks.has_key(name):
            iprint(c.white("Removing bookmark '%s'" % name))
            del bookmarks[name]
    else:
        usage_error("rmbookmark")
    

def bookmark(*args):
    global bookmarks
    if len(args[0]) == 1:
        name = args[0][0]
        if bookmarks.has_key(name):
            warning("Replacing bookmark %s" % name)
        iprint(c.white("Storing bookmark ") + c.green(name) + c.blue(" -> ") + c.red(path))
        bookmarks[name] = path
    else:
        usage_error("bookmark")
    
def goto(*args):
    global bookmarks
    if len(args[0]) == 1:
        name = args[0][0]
        if not bookmarks.has_key(name):
            error("No such bookmark %s" % name)
            return
        
        iprint(c.white("Taking you to ") + c.green(bookmarks[name]))
        if bookmarks[name] == "/NetObjects":
            cd(["/"])
        else:
            cd([bookmarks[name]])
            
    elif len(args[0]) == 0:
        for key in bookmarks.iterkeys():
            iprint(c.green(key) + c.blue(" -> ") + c.red(bookmarks[key]))

def simplepmt(*args):
    global simpleprompt
    simpleprompt = not simpleprompt
    
def exporttree(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    else:
        script = None
        if len(args[0]) == 1:
            script = args[0][0]
            
        lines = []
        lines.append("# Generated by pyplcli version %s" % SCRIPT_VERSION)
        
        lines.append("cd /")
        
        objs = rs.object_list(path, recursive=True)
        for obj in objs:
            pth = os.path.join(obj.path, obj.name).replace("/NetObjects/", "")
            lines.append("mkdir %s" % pth)
            if len(obj.items) > 0:
                lines.append("cd %s" % pth)
                for i in obj.items:
                    if i.value2 == "":
                        lines.append("add %s" % i.value1)
                    else:
                        lines.append("add %s/%s" % (i.value1, i.value2))
                lines.append("cd /")

        if script is not None:
            iprint(c.white("Writing tree to file %s" % script))
            f = open(script, "w")
            for line in lines:
                f.write(line + "\n")
            f.close()
            iprint(c.white("Wrote %d lines to %s" % (len(lines), script)))
        else:
            for line in lines:
                if line.startswith("#"):
                    iprint(c.brown(line))
                else:
                    parts = line.split(" ")
                    iprint(c.green(parts[0]) + " " + c.yellow(" ".join(parts[1:])))
                    
def _internal_grep(pattern, case_sensitive=True, recursive=False):
    global output_buffer, buffer_output
    buffer_output = True
    if recursive:
        tree([])
    else:
        ls([path])
    buffer_output = False
    pattern = pattern.lower() if not case_sensitive else pattern
    for line in output_buffer:
        fline = line.lower() if not case_sensitive else line
        if pattern in fline:
            iprint(line, newline=False)
    output_buffer = []
    
def grep(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    elif len(args[0]) > 0:
        _internal_grep(" ".join(args[0]), case_sensitive=True)
    else:
        usage_error("grep")
    
def igrep(*args):
    if pl is None:
        error("Not connected to any PacketLogic")
    elif len(args[0]) > 0:
        _internal_grep(" ".join(args[0]), case_sensitive=False)
    else:
        usage_error("igrep")

# Mapping between the text names and the python methods
# First item in list is a method handle and second is a help string used by the
# 'help' command.

functions = {
    'quit'          : [quit,            "Quit the program"],
    'exit'          : [quit,            "Quit the program"],
    'connect'       : [connect,         "Connect to a server\n\tUsage: connect HOSTNAME [USERNAME] [PASSWORD]"],
    'ls'            : [ls,              "List current path - just like the command you know and love"],
    'll'            : [lsl,             "Like ls but a bit more information\n\tHeaders: id, type, created, modified, creator, name/value"],
    'cd'            : [cd,              "Go to a specific path"],
    'pwd'           : [pwd,             'Print "working directory"'],
    'history'       : [history,         'Print command history'],
    'help'          : [hlp,             'This help message'],
    'connections'   : [con,             "List saved connections"],
    'config'        : [config,          "List configuration information for current connection\n\tUsage: config [CONFIG_VALUE]"],
    'disconnect'    : [disconnect,      "Disconnects from the current PacketLogic"],
    'mono'          : [mono,            "Turn off color support"],
    'color'         : [color,           "Turn on color support"],
    'update'        : [update,          "Update pyplcli.py to the latest version from github.com"],
    'mkdir'         : [mkdir,           "Create a NetObject at current pwd\n\tUsage: mkdir NAME"],
    'rm'            : [remove,          "Delete a NetObject at current pwd\n\tUsage: rm DIR"],
    'dynadd'        : [dynadd,          "Add a dynamic item at current pwd\n\tUsage: dynadd IP [SUBSCRIBER_NAME]"],
    'dynrm'         : [dynrm,           "Remove a dynamic item.\n\tUsage: dynrm all|IP|SUBSCRIBER_NAME\n\n\t" + c.red("Note: all dynamic items matching IP and SUBSCRIBER_NAME will be removed. Not only in PWD.")],
    'dynlist'       : [dynlist,         "List dynamic items at current pwd\n\tUse flag all to list all dynamic items of the PRE"],
    'tree'          : [tree,            "Recursively list all objects at pwd"],
    'record'        : [record,          "Record a macro\n\tUsage: record MACRO_NAME"],
    'stop'          : [stop,            "Stop macro recording"],
    'play'          : [play,            "Play a macro\n\tUsage: play MACRO_NAME"],
    'rmmacro'       : [rmmacro,         "Remove a macro\n\tUsage: rmmacro MACRO_NAME"],
    'list'          : [list_macro,      "List macros or command of a macro\n\tUsage: list [MACRO_NAME]"],
    'lv'            : [liveview,        "Display a simple LiveView (for current path) - exit with CTRL+c"],
    'clear'         : [clear,           "Clear the screen"],
    'top'           : [top,             "System diagnostics"],
    'visible'       : [visible,         "Toggle visibility in LiveView for current pwd"],
    'portobject'    : [portobject,      "Manipulate port objects\n\tUsage portobject add|remove|list"],
    'add'           : [add_item,        "Add a NetObject item to current pwd\n\tUsage: add 0.0.0.0 | 0.0.0.0-1.1.1.1 | 0.0.0.0/255.255.255.0"],
    'del'           : [del_item,        "Delete a NetObject item from current pwd\n\tUsage: del 0.0.0.0 | 0.0.0.0-1.1.1.1 | 0.0.0.0/255.255.255.0"],
    'version'       : [version,         "Display version and changelog history"],
    'hosts'         : [hosts,           "Get hosts from <Ungrouped> NetObject (pwd)\n\tUsage: hosts [MAX=500]"],
    'run'           : [runscript,       "Executes a script file.\n\tUsage: run SCRIPT_PATH"],
    'edit'          : [editscript,      "Launches $EDITOR for editing a macro or file. \n\tUsage: edit FILE | MACRO"],
    'alias'         : [alias,           "Create an alias for a command.\n\tUsage: alias [NAME] [COMMAND]"],
    'rmalias'       : [rmalias,         "Remove an alias.\n\tUsage: rmalias NAME"],
    'bookmark'      : [bookmark,        "Create a bookmark at pwd (use goto to go back later)\n\tUsage: bookmark MAME"],
    'rmbookmark'    : [rmbookmark,      "Removes a bookmark.\n\tUsage: rmbookmark BOOKMARK"],
    'goto'          : [goto,            "Go to a bookmarked location. If used with no arguments it lists the bookmarks.\n\tUsage: goto [BOOKMARK]"],
    'simpleprompt'  : [simplepmt,       "Toggle simple or advanced prompt."],
    'exporttree'    : [exporttree,      "Export the NetObject tree as a pli script.\n\tUsage: exporttree [SCRIPTFILE]"],
    'grep'          : [grep,            "Works like the grep command you know and love. Will always assume you grep in PWD. \n\tUsage: grep TEXT"],
    'igrep'         : [igrep,           "Works like the grep -i (case insensitive) command you know and love. Will always assume you grep in PWD. \n\tUsage: grep TEXT"],
}

#############################################################################
############################  End of commands ###############################
#############################################################################


#############################################################################
############################  Output Helpers  ###############################
#############################################################################

def usage_error(command):
    error("Incorrect usage")
    iprint(c.light_green(functions[command][1]))
    print

def error(message):
    print
    iprint(c.error("Error:") + " " + c.yellow(message))
    print
    
def warning(message):
    iprint(c.yellow("Warning: ") + c.white(message))

def save_log(msg):
    """
        For future use.
    """
    return msg

def extended_usage():
    for key in sorted(functions.iterkeys()):
        iprint(c.yellow(key))
        iprint("\t" + c.white(functions[key][1]))
        print

def usage():
    iprint(c.white("Command line help for pyplcli"))
    iprint(c.white("-----------------------------"))
    
    print
    iprint(c.white("Usage: ") + c.green("python pyplcli [args]"))
    iprint(c.white("Running pyplcli with no arguments will enter interactive mode."))
    print
    iprint(c.white("Arguments:"))
    print
    iprint(c.red("\t-h|--help"))
    iprint(c.white("\t\tShow this help message"))
    
    iprint(c.red("\t-s|--script"))
    iprint(c.white("\t\tRun a script file (PLI) and then exit"))
    
    iprint(c.red("\t-i|--import"))
    iprint(c.white("\t\tImports a script file to the internal macros\n\t\t(saved in %s)" % MACRO_DIR))
    
    iprint(c.red("\t-e|--execute"))
    iprint(c.white("\t\tExecutes commands from CLI and then exits"))
    
    iprint(c.red("\t-r|--run"))
    iprint(c.white("\t\tRun an internal macro file (PLI) and then exit.\n\t\tUse '-l all' to see available macros"))

    iprint(c.red("\t-q|--quiet"))
    iprint(c.white("\t\tSupress output while running scripts/macros"))
    
    iprint(c.red("\t-l|--list"))
    iprint(c.white("\t\tLists the contens of an internal macro. If 'all'\n\t\tis passed, a list of all macros will be presented."))
    
    iprint(c.red("\t-c|--commands"))
    iprint(c.white("\t\tPrints a full help for all commands"))
    
    iprint(c.red("\t-p|--packetlogics"))
    iprint(c.white("\t\tLists all saved connections"))
    
    iprint(c.red("\t-o|--open"))
    iprint(c.white("\t\tConnect to a saved PacketLogic on startup (use '-p')"))
    
    print

#############################################################################
############################  Internal stuff  ###############################
#############################################################################

def tc(text, state):
    """
        Called when autocomplete is required.
    """
    options = functions.keys()
    matches = []
    buf = readline.get_line_buffer().split()
    command = buf[0]
    if command in options:
        # We have a full command
        if command == "connect":
            matches = [s for s in connections.keys() if s and s.startswith(text)]
        elif command == "cd" or command == "ls" or command == "rm":
            if pl is not None:
                objs = rs.object_list(path, recursive=False)
                items = [o.name for o in objs]
                matches = [s for s in items if s and s.startswith(text)]
        elif command == "config":
            if pl is not None:
                tmp = cfg.list()
                items = [i["key"] for i in tmp]
                matches = [s for s in items if s and s.startswith(text)]
        elif command == "play" or command == "rmmacro" or command == "list":
            matches = [s for s in macros.keys() if s and s.startswith(text)]
        elif command == "rmalias":
            matches = [s for s in aliases.keys() if s and s.startswith(text)]
        elif command == "help":
            matches = [s for s in options if s and s.startswith(text)]
        elif command == "portobject":
            matches = [ s for s in ["add", "remove", "list"] if s and s.startswith(text)]
        elif command == "del":
            if pl is not None:
                obj = rs.object_find(path)
                items = []
                for item in obj.items:
                    extra = "" if not item.value2 else "/" + item.value2
                    txt = item.value1 + extra
                    items.append(txt)
                matches = [s for s in items if s and s.startswith(text)]
        elif command == "run":
            matches = [s for s in os.listdir(os.getcwd()) if s and s.startswith(text) and s.endswith(".pli")]
        elif command == "edit":
            matches = [s for s in os.listdir(os.getcwd()) if s and s.startswith(text) and s.endswith(".pli")]
            matches = matches + [s for s in macros.iterkeys() if s and s.startswith(text)]
        elif command == "goto" or command == "rmbookmark":
            matches = [s for s in bookmarks.iterkeys() if s and s.startswith(text)]
        else:
            pass
            #iprint(c.red("\nNo autocomplete support for '%s'" % command))

    else:        
        matches = [s for s in options if s and s.startswith(text)]
    
    if state > len(matches):
        return None
    else:
        return matches[state]

def save_state():
    """
        Called when the script exits. Saves states etc.
    """
    global s,c,connections, macros, macro_record, aliases, bookmarks
    c.verbose()
    iprint(c.white("Saving connection information..."),newline=False)
    try:
        if macro_record:
            stop()
        output = open(PICKLE_FILE, 'wb')
        pickle.dump(connections, output)
        iprint(c.green("OK"))
        iprint(c.white("Saving aliases... "),newline=False)
        pickle.dump(aliases, output)
        iprint(c.green("OK"))
        iprint(c.white("Saving bookmarks... "),newline=False)
        pickle.dump(bookmarks, output)
        iprint(c.green("OK"))
        iprint(c.white("Saving macros... "),newline=False)
        if not os.path.exists(MACRO_DIR):
            os.mkdir(MACRO_DIR)
        for macro, lines in macros.iteritems():
            handle = open(os.path.join(MACRO_DIR, macro + ".pli"), "w")
            for line in lines:
                handle.write(" ".join(line) + "\n")
            handle.close()
        output.close()
        iprint(c.green("OK"))
    except IOError:
        iprint(c.red("Failed"))

def dispatch(line):
    """
        Figures out what to do with a line from the prompt.
    """
    global macro_record, macros, current_macro
    if line.startswith("#"):
        if macro_record:
            if not macros.has_key(current_macro):
                macros[current_macro] = []
            macros[current_macro].append(line.split(" "))
        return
        
    parts = line.split()
    if len(parts) is 0:
        return
    
    if parts[0] in aliases.iterkeys():
        return dispatch(aliases[parts[0]])
    
    if not parts[0] in functions:
        error("Unknown command '%s'" % parts[0])
    else:
        if macro_record:
            if (not parts[0] == "record") and (not parts[0] == "stop"):
                if not macros.has_key(current_macro):
                    macros[current_macro] = []
                iprint(c.green("Recorded: ")  + c.white(" ".join(parts))    )
                macros[current_macro].append(parts)
        functions[parts[0]][0](parts[1:])

def prompt():
    """
        Renders the prompt and dispatches commands.
    """
    global buffer_output, output_buffer
    count = 0
    while True:
        try:
            pmt = c.blue(">> [%d]" % count) + c.red(" (%s@%s)" % (username, server)) + c.yellow(" (%s): " % path)
            if pl is None:
                pmt = c.blue(">> [%d]: " % count) + c.red("(disconnected): ")
            
            if simpleprompt:
                pmt = c.blue(">> ")
                
            line = raw_input(pmt)
            
            parts = line.split("|")
            filtr = None
            cmd = None
            if len(parts) == 2:
                line = parts[0]
                parts = parts[1].strip().split(" ")
                cmd = parts[0]
                filtr = " ".join(parts[1:])
                if cmd == "grep" or cmd == "igrep":
                    buffer_output = True
                    if cmd == "igrep":
                        filtr = filtr.lower()
                else:
                    filtr = None
                    error("Unknown filter command '%s'" % cmd)
                    continue
            
            parts = line.split(";")
            for part in parts:
                dispatch(part)
                count = count + 1
                
            if filtr is not None:
                buffer_output = False
                for line in output_buffer:
                    fline = line
                    if cmd == "igrep":
                        fline = line.lower()
                    if filtr in fline:
                        iprint(line, newline=False)
                output_buffer = []
                
        except KeyboardInterrupt:
            iprint()
            quit()
        except EOFError:
            print
            quit()

def load_script(script):
    """
        Load a script into the in memory macro list.
    """
    global macros
    sname = os.path.splitext(os.path.basename(script))[0]
    macros[sname] = []
    handle = open(script, "r")
    for line in handle.readlines():
        line = line.strip()
        if line == "":
            continue
        macros[sname].append(line.split(" "))

def run_script(script, exit_after=True):
    """
        Executes a script file.
    """
    iprint(c.white("Loading script %s... " % script),newline=False)
    macro = []
    handle = open(script, "r")
    for line in handle.readlines():
        line = line.strip()
        if line == "":
            continue
        macro.append(line.split(" "))
    iprint(c.green("OK"))
    iprint(c.white("Executing script"))
    for line in macro:
        if not line[0].startswith("#"):
            iprint(c.green("Executing: ") + c.white(" ".join(line)))
            if functions.has_key(str(line[0])):
                functions[str(line[0])][0](line[1:])
            else:
                iprint(c.red("Command error: ") + c.white("command '%s' not found." % str(line[0])))
                count = 1
                for x in macro:
                    x = " ".join(x)
                    y = " ".join(line)
                    if x == y:
                        iprint(c.white(" %02d: " % count) + c.red(x) + c.yellow("  <-- Failing command"))
                    else:
                        iprint(c.white(" %02d: %s" % (count, x)))
                    count += 1
                if exit_after:
                    sys.exit(1)
    if exit_after:
        sys.exit(0)

def load_module(code_path):
    try:
        try:
            code_dir = os.path.dirname(code_path)
            code_file = os.path.basename(code_path)
            fin = open(code_path, 'rb')
            return  imp.load_source(hashlib.md5(code_path).hexdigest(), code_path, fin)
        except SyntaxError, e:
            error("Syntax error in plugin '%s'" % code_path)
            iprint(c.red(str(e)))
            return None
        finally:
            try: fin.close()
            except: pass
    except ImportError, x:
        traceback.print_exc(file = sys.stderr)
        raise
    except:
        traceback.print_exc(file = sys.stderr)
        raise        

def update_plugins(eventtype = "", payload = ""):
    global pl, rs, rt, c, s, connections
    
    for plugin in plugins.iterkeys():
        plugins[plugin].pl = pl
        plugins[plugin].pl = rs
        plugins[plugin].pl = rt
        plugins[plugin].c = c
        plugins[plugin].s = s
        plugins[plugin].connections = connections
        plugins[plugin].iprint = iprint
            
    for plugin in plugins.iterkeys():
        if eventtype in plugins[plugin].plugin_callbacks.keys():
            plugins[plugin].plugin_callbacks[eventtype](payload)

def iprint(message="", newline=True):
    global buffer_output, output_buffer
    if buffer_output:
        cr = "\n" if newline else ""
        output_buffer.append(message + cr)
    else:
        if newline:
            print message
        else:
            print message,

def main():
    global s,c, connections, macros, aliases, bookmarks
    
    s.clear()
    iprint(c.yellow("Procera Networks Python CLI") + c.red(" v%s" % SCRIPT_VERSION) + "\n")
    iprint(c.white("Welcome to the interactive console"))
    iprint(c.white("To get a list of commands, type help\n"))
    iprint(c.white("Initializing..."))
    
    # Initialize readline
    try:
        iprint(c.white("Reading command history..."),newline=False)
        if os.path.exists(HISTORY_FILE):
            readline.read_history_file(HISTORY_FILE)
            iprint(c.green("OK"))
        else:
            iprint(c.green("No history found"))
    except IOError:
        iprint(c.red("Error: ") + "Could not read history file '%s'" % HISTORY_FILE)
        sys.exit(1) 
    
    readline.parse_and_bind('"\C-l": clear-screen')
    
    if platform.system() == 'Darwin':
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind('tab: complete')
        readline.parse_and_bind('"\C-r": reverse-search-history')
        readline.parse_and_bind('"\C-s": forward-search-history')
        readline.parse_and_bind('"\C-p": previous-history')
        readline.parse_and_bind('"\C-n": next-history')
    
    readline.parse_and_bind('set editing-mode vi')
    # This forces readline to automatically print the above list when tab
    # completion is set to 'complete'.
    readline.parse_and_bind('set show-all-if-ambiguous on')
    # Bindings for incremental searches in the history. These searches
    # use the string typed so far on the command line and search
    # anything in the previous input history containing them.
    
    readline.set_completer(tc)
    
    iprint(c.white("Loading connection data... "),newline=False)
    if os.path.exists(PICKLE_FILE):
        con_data = open(PICKLE_FILE, 'rb')
        try:
            connections = pickle.load(con_data)
            iprint(c.green("OK"))
        except:
            iprint(c.red("Failed"))
            iprint(c.white("Please remove the file: '%s' and restart" % PICKLE_FILE))
        iprint(c.white("Loading aliases... "),newline=False)
        try:
            aliases = pickle.load(con_data)
            iprint(c.green("OK"))
        except:
            iprint(c.red("Failed"))
            warning("There was a problem loading aliases")
            
        iprint(c.white("Loading bookmarks... "),newline=False)
        try:
            bookmarks = pickle.load(con_data)
            iprint(c.green("OK"))
        except:
            iprint(c.red("Failed"))
            warning("There was a problem loading bookmarks")
            
        iprint(c.white("Loading macros... "),newline=False)
        if os.path.exists(MACRO_DIR):
            scripts = [os.path.join(MACRO_DIR, x) for x in os.listdir(MACRO_DIR)]
            for script in scripts:
                load_script(script)
        try:
            macros = pickle.load(con_data)
        except:
            pass
        
        
        iprint(c.green("OK"))
    else:
        iprint(c.green("No connections found"))
    
    iprint(c.white("Searching for plugins... "),newline=False)
    plugin_dir = None
    if os.path.exists(os.path.join(os.getcwd(), "plugins")):
        plugin_dir = os.path.join(os.getcwd(), "plugins")
        iprint(c.green("OK"))
    elif os.path.exists(os.path.join(os.environ["HOME"], ".pyplcli_plugins")):
        plugin_dir = os.path.join(os.environ["HOME"], ".pyplcli_plugins")
        iprint(c.green("OK"))
    else:
        iprint(c.red("Failed"))
    
    if plugin_dir is not None:
        for f in os.listdir(plugin_dir):
            if f.startswith("plugin") and f.endswith(".py"):
                plug = load_module(os.path.join(plugin_dir, f))
                if plug is None:
                    continue
                if plug.LOAD:
                    plugins[f] = plug
                    try:
                        plug.plugin_callbacks
                    except AttributeError:
                        error("Could not load plugin '%s'. Make sure plugin_callbacks is defined as a dict." % f)
                        del plugins[f]
                        continue
                    try:
                        for key in plug.plugin_functions.keys():
                            functions[key] = plug.plugin_functions[key]
                            functions[key][1] = "Contributed from plugin: %s\n\t" % c.green(f) + functions[key][1]
                    except AttributeError:
                        error("Could not load plugin '%s'. Make sure plugin_functions is defined as a dict." % f)
                        del plugins[f]
                        continue

        update_plugins("init", "Initializing plugins")

    atexit.register(readline.write_history_file, HISTORY_FILE)
    atexit.register(save_state)
    
    iprint("")
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hs:i:e:r:ql:cpo:v", ["help", "script=", "import=", "execute=", "run=", "quiet", "list=", "commands", "packetlogics", "open="])
    except getopt.GetoptError, err:
        iprint(str(err))
        usage()
        sys.exit(2)
        
    script = None
    execute = None
    run = None
    packetlogic = None
    
    for o, a in opts:
        if o == "-v":
            iprint(c.white("Version: ") + c.light_green(SCRIPT_VERSION))
            local_version = ""
            try:
                f = open(sys.argv[0], 'r')
                local_version = f.read()
                f.close()
            except:
                iprint(c.error("Error: ") + c.white("Could not read local version %s" % sys.argv[0]))
    
            local_md5 = hashlib.md5(local_version).hexdigest()
            iprint(c.white("MD5: ") + c.light_green(local_md5))
            iprint("")
            version()
            sys.exit(0)
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-c", "--commands"):
            extended_usage()
            sys.exit()
        elif o in ("-p", "--packetlogics"):
            iprint(c.white("List of saved connections:"))
            for conn, vals in connections.iteritems():
                if conn is not None:
                    iprint("* " + c.red(vals[0]) + c.white("@") + c.green(conn))
            print
            sys.exit()
        elif o in ("-s", "--script"):
            script = a
        elif o in ("-q", "--quiet"):
            c.be_quiet()
        elif o in ("-e", "--execute"):
            execute = a.split(";")
        elif o in ("-i", "--import"):
            iprint(c.white("Importing script %s" % a))
            load_script(a)
        elif o in ("-r", "--run"):
            run = [a]
        elif o in ("-o", "--open"):
            packetlogic = a
        elif o in ("-l", "--list"):
            if a == "all":
                iprint(c.white("List of all macros:"))
                for macro in macros.keys():
                    iprint(c.blue(macro))
                print
            elif a in macros.keys():
                count = 1
                for line in macros[a]:
                    iprint(c.white(" %02d: " % count) + c.blue(" ".join(line)))
                    count += 1
                print
                sys.exit(0)
            else:
                error("No such macro '%s'" % a)
            sys.exit(1)
        else:
            assert False, "unhandled option"
        
    if script is not None:
        if packetlogic is not None:
            connect([packetlogic])
        run_script(script)
    elif execute is not None:
        for line in execute:
            line = line.split(" ")
            iprint(c.green("Executing: ") + c.white(" ".join(line)))
            if functions.has_key(str(line[0])):
                functions[str(line[0])][0](line[1:])
            else:
                iprint(c.red("Command error: ") + c.white("command '%s' not found." % str(line[0])))
                count = 1
                for x in execute:
                    y = " ".join(line)
                    if x == y:
                        iprint(c.white(" %02d: " % count) + c.red(x) + c.yellow("  <-- Failing command"))
                    else:
                        iprint(c.white(" %02d: %s" % (count, x)))
                    count += 1
                sys.exit(1)
                    
        sys.exit(0)
    elif run is not None:
        iprint(c.white("Running macro %s" % a))
        play(run)
        sys.exit(0)
    else:
        c.verbose()
        if packetlogic is not None:
            connect([packetlogic])
        prompt()

if __name__ == '__main__':
    main()

