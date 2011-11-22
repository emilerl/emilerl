# pyplcli.py documentation

pyplcli.py is a command line utility for working with Procera Networks PacketLogic systems using the official Python API (see http://python.proceranetworks.com). It is designed to be standalone with no dependencies on anything but the standard Python library. It supports a lightweight plugin framework for extensions and is fully scriptable.

# Macros
A pyplcli.py macro is simply a text file containing commands, one per line. Lines starting with a #-character will be ignored.

# Plug-ins
A plugin is a standard Python module located in either $HOME/.pyplcli\_plugins or a "plugins" sub-folder of the folder where pyplcli.py resides. A plugin file must be named plugin\_name.py to be loaded. 

A plugin file must define the following variables, else it will not be loaded.

    LOAD = False
    
This tells pyplcli.py if the plugin should be loaded at start or not.

    c = None   # Color manipulation
    s = None   # Screen manipulation
    pl = None  # A PacketLogic reference
    rs = None  # A reference to the Ruleset
    rt = None  # A reference to the Realtime
    connections = {} # A reference to the connections list

These variables are runtime variables in pyplcli.py that are shared with the plugins. The might be updated at any time. Modifying them will also modify them in the main program as they are references, not copies.
    
    plugin_functions = {
        "hello":    [hello, "A good command explanation.\n\tUsage: hello"],
    }
    
This dict defines commands that the plugin offers to the host. The dict key is equivivalent of the command you will type at the prompt. The first item of the list is a function that will be called when the command is executed. pyplcli.py assumes that all command functions have the following signature:

    def command(*args)
    
No return value is required.

    plugin_callbacks = {
        "init"        : callback,
        "connection"  : callback,
    }
    
This dict mapps event handlers for different events to callback functions. These callbacks will be executed when certain events occur in the main program.

# Files
pyplcli.py relies on some external files for successful operation. It also automatically creates some files to keep persistency. The following files are created the first time pyplcli.py is executed, and updated upon exit:

    PICKLE_FILE     = os.path.join(os.environ["HOME"], ".pyplcli.pickle")
    HISTORY_FILE    = os.path.join(os.environ["HOME"], ".pyplcli_history")
    
If the $HOME folder of the user running pyplcli.py contains a hidden folder called .pyplcli\_macros, any .pli files in there will be loaded. This folder will also be created if the user saves macros from within the program.

    MACRO_DIR       = os.path.join(os.environ["HOME"], ".pyplcli_macros")
    
Plugins will be loaded, first from $PWD/plugins, secondly from $HOME/.pyplcli\_plugins. pyplcli.py will never create these folders automatically if they don't exist.

    plugin_dir = os.path.join(os.getcwd(), "plugins")
    plugin_dir = os.path.join(os.environ["HOME"], ".pyplcli_plugins")