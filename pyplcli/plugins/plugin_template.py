# encoding: utf-8
"""
plugin_example.py

Created by Emil Erlandsson on 2011-09-13.
Copyright (c) 2011 Emil Erlandsson. All rights reserved.

This is an example file of a plugin implementation for pyplcli.py.
"""
import sys

# This flag indicate if this plugin should be loaded at start or not.
LOAD = False

# Variables
# These variables will be set by the plugin host. They do not need to be 
# pre-defined. They are just here as a reminder that they are available.
c = None   # Color manipulation
s = None   # Screen manipulation
pl = None  # A PacketLogic reference
rs = None  # A reference to the Ruleset
rt = None  # A reference to the Realtime
connections = {} # A reference to the connections list

# Functions
def hello(*args):
    print "hey from plugin" 

def event_callback(args=None):
    print args

# This dictionary is necessary for mapping function names to functions and
# help messages. The format shall be:
#
# "name": [function, "Help message"]
#
plugin_functions = {
    "hello":    [hello, "A good command explanation.\n\tUsage: hello"],
}

# This dictionary is necessary for callbacks from pyplcli.py to the plugins
# for different events.
plugin_callbacks = {
    "init"    : event_callback,
    "update"   : event_callback,
}

if __name__ == "__main__":
    print "This module should only be loaded by pyplcli.py. Not to be executed directly."