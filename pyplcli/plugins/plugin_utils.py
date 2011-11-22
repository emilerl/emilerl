# encoding: utf-8
"""
plugin_example.py

Created by Emil Erlandsson on 2011-09-13.
Copyright (c) 2011 Emil Erlandsson. All rights reserved.

This is an example file of a plugin implementation for pyplcli.py.
"""
import sys
import socket
import urllib

# This flag indicate if this plugin should be loaded at start or not.
LOAD = True

c = None   # Color manipulation
s = None   # Screen manipulation
pl = None  # A PacketLogic reference
rs = None  # A reference to the Ruleset
rt = None  # A reference to the Realtime
connections = {} 

def usage_error(command):
    error("Incorrect usage")
    print "\t" + c.light_green(plugin_functions[command][1])
    print

def error(message):
    print
    print c.error("Error:") + " " + c.yellow(message)
    print

# Functions
def udpsend(*args):
    if len(args[0]) == 3:
        host = args[0][0]
        port = int(args[0][1])
        message = args[0][2]
        import socket
        udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udpSock.sendto(message, (host, port))
    else:
        usage_error("udpsend")

def psmimport(*args):
    global connections
    try:
        import cjson
    except:
        error("python module cjson not available.")
        print c.green("Try: ") + c.white("'sudo easy_install cjson' from command line, or")
        print c.green("Try: ") + c.white("'sudo apt-get install python-cjson'")
        return None
        
    if len(args[0]) != 3:
        usage_error("psmimport")
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
                    

plugin_functions = {
    'udpsend'       : [udpsend,         "Send a string as UDP message to host\n\tUsage: udpsend HOST PORT MESSAGE"],
    'psmimport'     : [psmimport,       "Import connections from PSM\n\tExample: psmimport HOST USERNAME PASSWORD"],
}
plugin_callbacks = {}

if __name__ == "__main__":
    print "This module should only be loaded by pyplcli.py. Not to be executed directly."