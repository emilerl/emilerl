#!/usr/bin/env python
# encoding: utf-8
"""
pyplcli.py

Created by Emil Erlandsson <eerlandsson@proceranetworks.com>
Copyright (c) 2011 Procera Networks. All rights reserved.

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
SCRIPT_VERSION = "0.9.1"

# TODO
# * dump/load NetObject tree states, including dynitems and tree in ASCII form
# * Add support for relative paths to cd
# * Clean up code for ls, lsl and tree
# * Fix autocomlpete
# * add support for adding port and other objects

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

try:
    import packetlogic2
except:
    print "PacketLogic Python API required for this script to run."
    print "Go to http://download.proceranetworks.com and download the correct"
    print "version for your machine."

PICKLE_FILE     = os.path.join(os.environ["HOME"], ".pyplcli.pickle")
HISTORY_FILE    = os.path.join(os.environ["HOME"], ".pyplcli_history")
MACRO_DIR       = os.path.join(os.environ["HOME"], ".pyplcli_macros")
SCRIPT_URL      = "https://github.com/emilerl/emilerl/raw/master/pyplcli/pyplcli.py"

# Bash utility functions
RESET = '\033[0m'
CCODES = {
    'black'           :'\033[0;30m',
    'blue'            :'\033[0;34m',
    'green'           :'\033[0;32m',
    'cyan'            :'\033[0;36m',
    'red'             :'\033[0;31m',
    'purple'          :'\033[0;35m',
    'brown'           :'\033[0;33m',
    'light_gray'      :'\033[0;37m',
    'dark_gray'       :'\033[0;30m',
    'light_blue'      :'\033[0;34m',
    'light_green'     :'\033[0;32m',
    'light_cyan'      :'\033[0;36m',
    'light_red'       :'\033[0;31m',
    'light_purple'    :'\033[0;35m',
    'yellow'          :'\033[0;33m',
    'white'           :'\033[0;37m',
}

MCODES = {
    'POS_LC'            : '\033[%d;%dH',
    'MOVE_UP_N'         : '\033[%dA',
    'MOVE_DOWN_N'       : '\033[%dB',
    'MOVE_FORWARD_N'    : '\033[%dC',
    'MOVE_BACK_N'       : '\033[%dD',
    'CLEAR'             : '\033[2J',
    'ERASE_EOL'         : '\033[K',
    'SAVE'              : '\033[s',
    'RESTORE'           : '\033[u',
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
        print MCODES["MOVE_BACKWARD_N"] % cols,
    
    def position(self, x, y):
        "x=line, y=column"
        print MCODES["POS_LC"] % (x,y),
    
    def clear(self):
        print MCODES["CLEAR"],
        
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
                    
# EO: Bash utility functions

connections = {}
macros = {}
macro_buffer = []
macro_record = False
current_macro = ""
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


#############################################################################
############################  "Shell commands" ##############################
#############################################################################

# command methods. As we don't know how many arguments the user will
# supply on the command line, each method must accept a variable length
# argument list (*args)

def not_implemented(*args):
    print c.red("Error: ") + c.white("This command is not implemented yet.")
    print c.green("Tip: ") + c.white("Try the 'update' command to see if there is a new version of the script.")

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
    
    github_md5 = hashlib.md5(github_version).hexdigest()
    local_md5 = hashlib.md5(local_version).hexdigest()
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
                backup_file = sys.argv[0].split(".")[0] + "-backup.py"
                print c.white("Creating backup file ") + c.green(sys.argv[0].split(".")[0])
                try:
                    shutil.copyfile(sys.argv[0], backup_file)
                    f = open(sys.argv[0], "w")
                    f.write(github_version)
                    f.close()
                    
                    print c.green("File updated!")
                    print c.white("Removing temporary update file %s" % prefix + "-%s.py..." % github_md5),
                    try:
                        os.remove(prefix + "-%s.py" % github_md5)
                        print c.green("OK")
                    except:
                        print c.red("Failed")
                    print c.white("Restartint pyplcli for the changes to have effect.")
                    sys.stdout.flush()
                    disconnect()
                    save_state()
                    subprocess.Popen(["/usr/bin/env","python",os.path.join(os.getcwd(),sys.argv[0])])
                except:
                    print c.red("Error: ") + c.white("Could not update automatic. Run manual update")
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
    else:
        print c.white("Local fingerprint:  ") + c.green(local_md5)
        print c.white("Github fingerprint: ") + c.green(github_md5)
        print c.white("No new update on github")
        

def quit(*args):
    print c.white("Exiting...")
    disconnect()
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
            print c.red("Error: " + c.white("No such connection %s" % s))
            return 
    elif len(args[0]) < 3:
        print c.red("Error: ") + c.white("Not enough parameters")
        print c.green("Usage: ") + c.white("connect <host> <username> <password>")
        return
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
        connections[s] = (u, p)
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

def reconnect():
    global pl, rs, rt, cfg
    disconnect()
    print c.white("Re-connecting..."),
    try:
        pl = packetlogic2.connect(server, username, password)
        rs = pl.Ruleset()
        rt = pl.Realtime()
        cfg = pl.Config()
        print c.green("Ok")
    except RuntimeError:
        print c.red("Failed")
        print c.white("Check your credentials or network connection") 

def dynrm(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            ip = args[0][0]
            o = rs.object_find(path)
            if o is not None:
                print c.white("Removing") + c.green(" %s" % (ip)) + c.white(" from ") + c.red(path)
                rt.dyn_remove(o.id, ip)
            else:
                print c.red("Error: ") + c.white("cannot add dynitems in %s" % path)
        else:
            print c.red("Error: ") + c.white("correct usage is dynrm IP")

def dynadd(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            ip = args[0][0]
            subscriber = None
            if len(args[0]) >= 2:
                subscriber = " ".join(args[0][1:])
            o = rs.object_find(path)
            if o is not None:
                print c.white("Adding") + c.green(" (%s, %s)" % (ip, subscriber)) + c.white(" to ") + c.red(path)
                rt.dyn_add(o.id, ip, subscriber)
            else:
                print c.red("Error: ") + c.white("cannot add dynitems in %s" % path)
        else:
            print c.red("Error: ") + c.white("correct usage is dynadd IP [Subscriber_name]")

def dynlist(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            if args[0][0] == "all":
                print c.white("Listing all the dynamic items")
                dynitems = rt.dyn_list_full()
                for noid,ip,sub in dynitems:
                    no = rs.object_find_id('/NetObjects', noid)
                    if no is not None:
                        print c.white(os.path.join(no.path, no.name) + "/") + c.light_green(ip) + " " + c.red("(%s)" % sub)
                    else:
                        print c.red("No parent: ") + c.light_green(ip) + " " + c.red("(%s)" % sub)
            else:
                print c.red("Error:") + c.white(" '%s' is not a valid flag for dynlist" % args[0][0])
        else:
            print c.white("Listing the dynamic items of ") + c.green(path)
            obj = rs.object_find(path)
            if obj is not None:
                dynitems = rt.dyn_list_no(obj.id)
                for i,j in dynitems:
                    print c.light_green(j)  

def ls(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        tmp_path = path
        if len(args[0]) > 0:
            tmp_path = os.path.join(path, args[0][0])
        print c.white("Listing the contents of ") + c.green(tmp_path)
        objs = rs.object_list(tmp_path, recursive=False)
        for obj in objs:
            print c.blue(obj.name)
        o = rs.object_find(tmp_path)
        if o is not None:
            for i in o.items:
                extra = "" if i.value2 == "" else "/" + c.purple(str(i.value2))
                print c.purple(str(i.value1)) + extra

def tree(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        print c.white("Listing the contents of ") + c.green(path)
        objs = rs.object_list(path, recursive=True)
        for obj in objs:
            print c.green(obj.path) + "/" +c.blue(obj.name)
            if obj is not None:
                for i in obj.items:
                    print c.green(obj.path) + "/" +c.purple(i.value1) + "/" + c.purple(i.value2)


def lsl(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        tmp_path = path
        if len(args[0]) > 0:
            tmp_path = os.path.join(path, args[0][0])
        print c.white("Listing the contents of ") + c.green(tmp_path)
        objs = rs.object_list(tmp_path, recursive=False)
        for obj in objs:
            print c.white("%8d" % obj.id + "  " + str(obj.type) + "  " + str(obj.creation_date) + "  " + str(obj.modification_date) + "  " + c.yellow(str(obj.creator)) + "  ") + c.blue(obj.name)
        o = rs.object_find(path)
        if o is not None:
            for i in o.items:
                print c.white("%8d" % i.id + "  " + str(i.type) + "  " + str(i.creation_date) + "  " + str(i.modification_date) + "  " + c.yellow(str(i.creator)) + "  ") + c.purple(i.value1) + "/" + c.purple(i.value2)
        

def cd(*args):
    global path
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
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
            print tmp
            if o is None:
                print c.red("Error: ") + c.white("No such path in NetObject tree: '%s'" % tmp)
            else:
                path = tmp

def pwd(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        print c.white(path)

def mkdir(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            no_name = " ".join(args[0])
            print c.white("Creating NetObject path: ") + c.green("%s" % os.path.join(path, no_name))
            oid = rs.add(os.path.join(path, no_name))
            print c.white("New object id: %d" % oid)
            rs.commit()
        else:
            print c.red("Error: ") + c.white("Usage: mkdir name")

def remove(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            no_name = " ".join(args[0])
            what = os.path.join(path, no_name)
            o = rs.object_find(what)
            if o is not None:
                print c.white("Deleting NetObject path: ") + c.green("%s" % what)
                rs.object_remove(what)
                resp = raw_input(c.red("Are you sure you want to continue") + c.white(" (y/N)? : "))
                if resp == 'y':
                    rs.commit()
                else:
                    rs.rollback()
            else:
                print c.red("Error: ") + c.white("No such NetObject '%s'" % what)
        else:
            print c.red("Error: ") + c.white("Usage: mkdir name")

def history(*args):
    for i in range(readline.get_current_history_length()):
        print c.green("%d: " % i) + c.white(readline.get_history_item(i))

def hlp(*args):
    if len(args[0]) > 0:
        command = args[0][0]
        if command in functions.keys():
            print c.yellow(command)
            print "\t" + c.white(functions[command][1])
        else:
            print c.red("Unknown command '%s'" % command)
            print c.green("Tip: ") + c.white("Try 'help' for a list of commands")
    else:
        print c.yellow("Procera Networks Python CLI") + c.red(" v%s" % SCRIPT_VERSION) + "\n"
        print c.white("This is the interactive help\nHere is a list of all available commands\n")
        for key in sorted(functions.iterkeys()):
            print c.yellow(key)
            #print "\t" + c.white(functions[key][1])
        print c.white("\nUse 'help <command>' for more information on each command")

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
                items = [i["key"] for i in items if i["key"].startswith(key)]
                print c.green("Tip: " + c.white("Possible matches are %s" % str(items)))
        else:
            for i in cfg.list():
                print c.green(i["key"] + ": ") + c.white(str(i["value"]))

def disconnect(*args):
    global pl, rs, rt, cfg
    print c.white("Disconnecting..."),
    pl = None
    rs = None
    rt = None
    cfg = None
    print c.green("OK")

def mono(*args):
    global c
    c.disable()
    
def color(*args):
    global c
    c.enable()
    
def record(*args):
    global macro_record, current_macro
    if not macro_record:
        if len(args[0]) != 1:
            print c.red("Error: " + "Usage: record <macro name>")
        else:
            current_macro = args[0][0]
            if macros.has_key(current_macro):
                print c.yellow("Warning: " ) + c.white("Macro %s exists. All commands will be appended" % current_macro)
            macro_record = True
            print c.green("Macro recording started...")
    else:
        print c.red("Error: " + "Already recording .. this comman will not be recorded")
    
def stop(*args):
    global macro_record, current_macro
    if macro_record:
        macro_record = False
        current_macro = ""
        print c.red("Macro recording stopped...")
    else:
        print c.red("Error: " + "Not recording at the moment")

def list_macro(*args):
    global macro_record, macros
    if len(args[0]) == 0:
        for macro in macros.keys():
            print c.yellow(macro)
    elif len(args[0]) == 1:
        if macros.has_key(args[0][0]):
            for command in macros[args[0][0]]:
                print c.purple(" ".join(command))
    else:
        print c.red("No recorded macros")

def play(*args):
    if len(args[0]) == 1:
        if macros.has_key(args[0][0]):
            for command in macros[args[0][0]]:
                if not command[0].startswith("#"):
                    print c.green("Executing: ") + c.white(" ".join(command))
                    functions[str(command[0])][0](command[1:])
    
def rmmacro(*args):
    global macros
    if len(args[0]) == 1:
        if macros.has_key(args[0][0]):
            del macros[args[0][0]]

def liveview(*args):
    global rt, pl
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
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
                pass

            for m in data:
                if not counter > myscreen.getmaxyx()[0] - 2:
                    ratio = float(0)
                    if total != 0:
                        ratio = float((m.speed[0]*8.0/1000 + m.speed[1]*8.0/1000) / total)
                    if not c.disabled:  
                        myscreen.addstr(counter, 2, m.name + (50 - len(m.name)) * " " + str(m.speed[0]*8.0/1000) + (15 - len(str(m.speed[0]*8.0/1000))) * " " + str(m.speed[1]*8.0/1000) + (15 - len(str(m.speed[1]*8.0/1000))) * " " + "%0.1f" % (ratio *100), curses.color_pair(3) )
                    else:
                        myscreen.addstr(counter, 2, m.name + (50 - len(m.name)) * " " + str(m.speed[0]*8.0/1000) + (15 - len(str(m.speed[0]*8.0/1000))) * " " + str(m.speed[1]*8.0/1000) + (15 - len(str(m.speed[1]*8.0/1000))) * " " + "%0.1f" % (ratio *100))
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
            rt.stop_updating()

        curses.endwin()
        print MCODES["CLEAR"]
        reconnect()
               
def clear(*args):
    print MCODES["CLEAR"]
    
def top(*args):
    data = rt.get_sysdiag_data()
    mem = data["General"]["Memory used"]["value"]
    cpu0 = data["General"]["CPU Usage (0)"]["value"]
    cpu1 = data["General"]["CPU Usage (1)"]["value"]
    print c.green("Memory usage: ") + str(mem)
    print c.green("CPU(0) usage: ") + str(cpu0)
    print c.green("CPU(1) usage: ") + str(cpu1)

def psmimport(*args):
    global connections
    try:
        import cjson
    except:
        print c.red("Error: ") + c.white("python module cjson not available.")
        print c.green("Try: ") + c.white("'sudo easy_install cjson' from command line, or")
        print c.green("Try: ") + c.white("'sudo apt-get install python-cjson'")
        return None
        
    if len(args[0]) != 3:
        pass
    else:
        url = "https://%s:%s@%s:8443/rest/configurator/configuration" % (args[0][1], args[0][2], args[0][0])
        filehandle = urllib.urlopen(url)
        fetched = filehandle.read()
        filehandle.close()
        data = cjson.decode(fetched)
        for item in data:
            if "com.proceranetworks.psm.provisioner" in item[0]:
                s = item[3]["ruleset"][0]
                u = item[3]["username"]
                p = item[3]["password"]
                print c.green("Found: ") + "%s@%s. Adding to connections" % (u,s)
                if connections.has_key(u):
                    print c.red("Error: ") + "%s was already in connections. Skipping."
                else:
                    connections[s] = (u,p)

def visible(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        o = rs.object_find(path)
        if o is not None:
            if o.visible:
                print c.white("NetObject ") + c.green("%s" % path) + c.white(" is visible. Setting visible to false.")
            else:
                print c.white("NetObject ") + c.green("%s" % path) + c.white(" is not visible. Setting visible to true.")
            o.set_visible(not o.visible)
            rs.commit()
        else:
            print c.red("Error: ") + c.white("cannot toggle visibility for %s" % path)

def portobject(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        cmds = ["list", "add", "remove"]
        if len(args[0]) > 0:
            cmd = args[0][0]
            if cmd == "list":
                objs = rs.object_list('/PortObjects')
                for obj in objs:
                    print c.light_green(os.path.join("/PortObjects", obj.name))
                    for i in obj.items:
                        print " * ITEM: %s" % i
        else:
            print c.red("Error: ") + c.white("correct usage is portobject add|remove|list <options>")

def add_item(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            item = args[0][0]
            print c.white("Adding: ") + c.green("%s" % item) + c.white(" to ") + c.red(path)
            o = rs.object_find(path)
            if o is not None:
                o.add(item)
                rs.commit()
            else:
                print c.red("Error: ") + c.white("Can not add item here: %s" % path)
        else:
            print c.red("Error: ") + c.white("Incorrect usage")
            print c.green(functions["add"][1])

def del_item(*args):
    if pl is None:
        print c.red("Error: ") + c.white("Not connected to any PacketLogic")
    else:
        if len(args[0]) > 0:
            item = args[0][0]
            
            o = rs.object_find(path)
            if o is not None:
                item = item.replace("/", "-") if "/" in item else item
                if item in o.items:
                    print c.white("Removing: ") + c.green("%s" % item) + c.white(" from ") + c.red(path)
                    o.remove(item)
                else:
                    print c.red("Error: ") + c.white("No such item '%s'" % item)
                rs.commit()
            else:
                print c.red("Error: ") + c.white("Can not remove item here: %s" % path)
        else:
            print c.red("Error: ") + c.white("Incorrect usage")
            print c.green(functions["del"][1])
            
            
# Mapping between the text names and the python methods
# First item in list is a method handle and second is a help string used by the
# 'help' command.

functions = {
    'quit'          : [quit,            "Quit the program"],
    'exit'          : [quit,            "Quit the program"],
    'connect'       : [connect,         "Connect to a server\n\tUsage: connect <hostname> <username> <password>"],
    'ls'            : [ls,              "List current path - just like the command you know and love"],
    'll'            : [lsl,             "Like ls but a bit more information\n\tHeaders: id, type, created, modified, creator, name/value"],
    'cd'            : [cd,              "Go to a specific path"],
    'pwd'           : [pwd,             'Print "working directory"'],
    'history'       : [history,         'Print command history'],
    'help'          : [hlp,             'This help message'],
    'connections'   : [con,             "List saved connections"],
    'config'        : [config,          "List configuration information for current connection"],
    'disconnect'    : [disconnect,      "Disconnects from the current PacketLogic"],
    'mono'          : [mono,            "Turn off color support"],
    'color'         : [color,           "Turn on color support"],
    'update'        : [update,          "Update pyplcli.py to the latest version from github.com"],
    'mkdir'         : [mkdir,           "Create a NetObject at current pwd\n\tUsage: mkdir name"],
    'rm'            : [remove,          "Delete a NetObject at current pwd\n\tUsage: rm dir"],
    'dynadd'        : [dynadd,          "Add a dynamic item at current pwd\n\tUsage: dynadd IP [subscriber_name]"],
    'dynrm'         : [dynrm,           "Remove a dynamic item at current pwd"],
    'dynlist'       : [dynlist,         "List dynamic items at current pwd\n\tUse flag all to list all dynamic items of the PRE"],
    'tree'          : [tree,            "Recursively list all objects at pwd"],
    'record'        : [record,          "Record a macro\n\tUsage: record <macro name>"],
    'stop'          : [stop,            "Stop macro recording"],
    'play'          : [play,            "Play a macro\n\tUsage: play <macro name>"],
    'rmmacro'       : [rmmacro,         "Remove a macro\n\tUsage: rmmacro <macro name>"],
    'list'          : [list_macro,      "List macros or command of a macro\n\tUsage: list <macro name>"],
    'lv'            : [liveview,        "Display a simple LiveView (for current path) - exit with CTRL+c"],
    'clear'         : [clear,           "Clear the screen"],
    'top'           : [top,             "System diagnostics"],
    'psmimport'     : [psmimport,       "Import connections from PSM\n\tExample: psmimport <host> <username> <password>"],
    'visible'       : [visible,         "Toggle visibility in LiveView for current pwd"],
    'portobject'    : [portobject,      "Manipulate port objects"],
    'add'           : [add_item,        "Add a NetObject item to current pwd\n\tUsage: add 0.0.0.0 | 0.0.0.0-1.1.1.1 | 0.0.0.0/255.255.255.0"],
    'del'           : [del_item,        "Delete a NetObject item from current pwd\n\tUsage: del 0.0.0.0 | 0.0.0.0-1.1.1.1 | 0.0.0.0/255.255.255.0"],
    
}

#############################################################################
############################  End of commands ###############################
#############################################################################

def tc(text, state):
    options = functions.keys()
    matches = []
    buf = readline.get_line_buffer().split()
    command = buf[0]
    if command in options:
        # We have a full command
        if command == "connect":
            matches = [s for s in connections.keys() if s and s.startswith(text)]
        elif command == "cd" or command == "ls" or command == "rm":
            #print text
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
    else:        
        matches = [s for s in options if s and s.startswith(text)]
    
    if state > len(matches):
        return None
    else:
        return matches[state]

def save_state():
    global s,c,connections, macros, macro_record
    c.verbose()
    print c.white("Saving connection & macro information..."),
    try:
        if macro_record:
            stop()
        output = open(PICKLE_FILE, 'wb')
        pickle.dump(connections, output)
        #pickle.dump(macros, output)
        if not os.path.exists(MACRO_DIR):
            os.mkdir(MACRO_DIR)
        for macro, lines in macros.iteritems():
            handle = open(os.path.join(MACRO_DIR, macro + ".pli"), "w")
            for line in lines:
                handle.write(" ".join(line) + "\n")
            handle.close()
        output.close()
        print c.green("OK")
    except IOError:
        print c.red("Failed")

def dispatch(line):
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
        
    if not parts[0] in functions:
        print c.red("Unknown command '%s'" % parts[0])
    else:
        if macro_record:
            if (not parts[0] == "record") and (not parts[0] == "stop"):
                if not macros.has_key(current_macro):
                    macros[current_macro] = []
                print c.green("Recorded: ")  + c.white(" ".join(parts))    
                macros[current_macro].append(parts)
        functions[parts[0]][0](parts[1:])

def prompt():
    count = 0
    while True:
        try:
            if pl is not None:
                line = raw_input(c.blue(">> [%d]" % count) + c.red(" (%s@%s)" % (username, server)) + c.yellow(" (%s): " % path))
            else:
                line = raw_input(c.blue(">> [%d]: " % count) + c.red("(disconnected): "))
            dispatch(line)
            count = count + 1
        except KeyboardInterrupt, EOFError:
            quit()

def load_script(script):
    global macros
    sname = os.path.splitext(os.path.basename(script))[0]
    macros[sname] = []
    handle = open(script, "r")
    for line in handle.readlines():
        line = line.strip()
        if line == "":
            continue
        macros[sname].append(line.split(" "))

def run_script(script):
    print c.white("Loading script %s... " % script),
    macro = []
    handle = open(script, "r")
    for line in handle.readlines():
        line = line.strip()
        if line == "":
            continue
        macro.append(line.split(" "))
    print c.green("OK")
    print c.white("Executing script")
    for line in macro:
        if not line.startswith("#"):
            print c.green("Executing: ") + c.white(" ".join(line))
            functions[str(line[0])][0](line[1:])
    sys.exit(0)

def extended_usage():
    for key in sorted(functions.iterkeys()):
        print c.yellow(key)
        print "\t" + c.white(functions[key][1])
        print

def usage():
    print c.white("Command line help for pyplcli")
    print c.white("-----------------------------")
    
    print
    print c.white("Usage: ") + c.green("python pyplcli [args]")
    print c.white("Running pyplcli with no arguments will enter interactive mode.")
    print
    print c.white("Arguments:")
    print
    print c.red("\t-h|--help")
    print c.white("\t\tShow this help message")
    
    print c.red("\t-s|--script")
    print c.white("\t\tRun a script file (PLI) and then exit")
    
    print c.red("\t-i|--import")
    print c.white("\t\tImports a script file to the internal macros\n\t\t(saved in %s)" % MACRO_DIR)
    
    print c.red("\t-e|--execute")
    print c.white("\t\tExecutes commands from CLI and then exits")
    
    print c.red("\t-r|--run")
    print c.white("\t\tRun an internal macro file (PLI) and then exit.\n\t\tUse '-l all' to see available macros")

    print c.red("\t-q|--quiet")
    print c.white("\t\tSupress output while running scripts/macros")
    
    print c.red("\t-l|--list")
    print c.white("\t\tLists the contens of an internal macro. If 'all'\n\t\tis passed, a list of all macros will be presented.")
    
    print c.red("\t-c|--commands")
    print c.white("\t\tPrints a full help for all commands")
    
    print c.red("\t-p|--packetlogics")
    print c.white("\t\tLists all saved connections")
    
    print c.red("\t-o|--open")
    print c.white("\t\tConnect to a saved PacketLogic on startup (use '-p')")
    
    print

def main():
    global s,c, connections, macros
    s.clear()
    s.position(1,0)
    print c.yellow("Procera Networks Python CLI") + c.red(" v%s" % SCRIPT_VERSION) + "\n"
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
    
    print c.white("Loading connection data... "),
    if os.path.exists(PICKLE_FILE):
        print c.green("OK")
        con_data = open(PICKLE_FILE, 'rb')
        connections = pickle.load(con_data)
        print c.white("Loading macros... "),
        if os.path.exists(MACRO_DIR):
            scripts = [os.path.join(MACRO_DIR, x) for x in os.listdir(MACRO_DIR)]
            for script in scripts:
                load_script(script)
        try:
            macros = pickle.load(con_data)
        except:
            pass
        
        
        print c.green("OK")
    else:
        print c.green("No connections found")
    
    atexit.register(readline.write_history_file, HISTORY_FILE)
    atexit.register(save_state)
    
    print ""
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hs:i:e:r:ql:cpo:v", ["help", "script=", "import=", "execute=", "run=", "quiet", "list=", "commands", "packetlogics", "open="])
    except getopt.GetoptError, err:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
        
    script = None
    execute = None
    run = None
    packetlogic = None
    
    for o, a in opts:
        if o == "-v":
            print c.white("Version: ") + c.light_green(SCRIPT_VERSION)
            local_version = ""
            try:
                f = open(sys.argv[0], 'r')
                local_version = f.read()
                f.close()
            except:
                print c.error("Error: ") + c.white("Could not read local version %s" % sys.argv[0])
    
            local_md5 = hashlib.md5(local_version).hexdigest()
            print c.white("MD5: ") + c.light_green(local_md5)
            print ""
            sys.exit(0)
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-c", "--commands"):
            extended_usage()
            sys.exit()
        elif o in ("-p", "--packetlogics"):
            print c.white("List of saved connections:")
            for conn, vals in connections.iteritems():
                if conn is not None:
                    print "* " + c.red(vals[0]) + c.white("@") + c.green(conn)
            print
            sys.exit()
        elif o in ("-s", "--script"):
            script = a
        elif o in ("-q", "--quiet"):
            c.be_quiet()
        elif o in ("-e", "--execute"):
            execute = a.split(";")
        elif o in ("-i", "--import"):
            print c.white("Importing script %s" % a)
            load_script(a)
        elif o in ("-r", "--run"):
            run = [a]
        elif o in ("-o", "--open"):
            packetlogic = a
        elif o in ("-l", "--list"):
            if a == "all":
                print c.white("List of all macros:")
                for macro in macros.keys():
                    print c.blue(macro)
                print
            elif a in macros.keys():
                count = 1
                for line in macros[a]:
                    print c.white(" %02d: " % count) + c.blue(" ".join(line))
                    count += 1
                print
                sys.exit(0)
            else:
                print c.red("Error: ") + c.white("No such macro '%s'" % a)
            sys.exit(1)
        else:
            assert False, "unhandled option"
        
    if script is not None:
        run_script(script)
    elif execute is not None:
        for line in execute:
            line = line.split(" ")
            print c.green("Executing: ") + c.white(" ".join(line))
            functions[str(line[0])][0](line[1:])
        sys.exit(0)
    elif run is not None:
        print c.white("Running macro %s" % a)
        play(run)
        sys.exit(0)
    else:
        c.verbose()
        if packetlogic is not None:
            connect([packetlogic])
        prompt()

if __name__ == '__main__':
    main()

