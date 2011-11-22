# encoding: utf-8
"""
plugin_utils.py

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
iprint = lambda x: x

def usage_error(command):
    error("Incorrect usage")
    iprint("\t" + c.light_green(plugin_functions[command][1]))
    iprint()

def error(message):
    iprint("")
    iprint(c.error("Error:") + " " + c.yellow(message))
    iprint("")

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

plugin_functions = {
    'udpsend'       : [udpsend,         "Send a string as UDP message to host\n\tUsage: udpsend HOST PORT MESSAGE"],
}
plugin_callbacks = {}

if __name__ == "__main__":
    print "This module should only be loaded by pyplcli.py. Not to be executed directly."