# encoding: utf-8
"""
plugin_psm.py

Created by Emil Erlandsson on 2011-09-13.
Copyright (c) 2011 Emil Erlandsson. All rights reserved.

This is an example file of a plugin implementation for pyplcli.py.
"""
import sys
import urllib

# This flag indicate if this plugin should be loaded at start or not.
LOAD = True

# Variables set by the host.
c = None   # Color manipulation
s = None   # Screen manipulation
pl = None  # A PacketLogic reference
rs = None  # A reference to the Ruleset
rt = None  # A reference to the Realtime
connections = {} # A reference to the connections list
iprint = lambda x: x # Printing function set if plugin is allowed to print.

psmhost = None
psmuser = None
psmpass = None

def usage_error(command):
    error("Incorrect usage")
    iprint("\t" + c.light_green(plugin_functions[command][1]))
    iprint("")

def error(message):
    iprint("")
    iprint(c.error("Error:") + " " + c.yellow(message))
    iprint("")

# Functions
def editconfig(*args):
    pass

def psm(*args):
    global psmhost, psmuser, psmpass
    if len(args[0]) == 0:
        if psmhost is not None:
            iprint("PSM host is set to: %s:%s@%s" % (c.blue(psmuser),c.blue(psmpass), c.red(psmhost)))
        else:
            iprint("No PSM connection added yet.")
    elif len(args[0]) == 3:
        psmhost = args[0][0]
        psmuser = args[0][1]
        psmpass = args[0][2]
        iprint(c.white("Trying to connect to %s:%s@%s:8443" % (c.blue(psmuser),c.blue(psmpass), c.red(psmhost))))

    else:
        usage_error("psm")
        return
        
def psmimport(*args):
    global connections
    try:
        import cjson
    except:
        error("python module cjson not available.")
        iprint(c.green("Try: ") + c.white("'sudo easy_install python-cjson' from command line, or"))
        iprint(c.green("Try: ") + c.white("'sudo apt-get install python-cjson'"))
        return None
        
    if len(args[0]) != 3:
        usage_error("psm-import")
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
                iprint(c.green("Found: ") + "%s@%s. Adding to connections" % (u,s))
                if connections.has_key(u):
                    error("%s was already in connections. Skipping.")
                else:
                    connections[s] = (u,p)
        
plugin_functions = {
    'psm'           :   [psm,          "Set PSM connectivity to use. Use this before any psm commands.\n\tUsage: psm HOST USERNAME PASSWORD"],
    'psm-editconfig':   [editconfig,   "Edit the PSM configuration. "],
    'psm-import'     :  [psmimport,    "Import connections from PSM\n\tExample: psmimport HOST USERNAME PASSWORD"],
}

plugin_callbacks = {}

if __name__ == "__main__":
    print "This module should only be loaded by pyplcli.py. Not to be executed directly."