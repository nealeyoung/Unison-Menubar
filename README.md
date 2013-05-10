Unison Menubar
==============

A Mac menubar item that runs the [Unison file synchronizer](http://www.cis.upenn.edu/~bcpierce/unison/) at regular intervals, and alerts in case of conflicts or errors.

This is alpha software.  It will probably take you an hour or more to install and configure it, and you might have to poke around in the Python source (just a few pages) to make it work for you.  I'm putting here on github just in case others might want to play with it.

### What you can find here:

* in ./src: source code, in Python.
* in ./downloads: download of a standalone app (built using py2app for an Intel-based Mac running OS X 10.8).

### PREREQUISITES (SOFTWARE):

We assume that Unison is already installed and configured on every machine that you want to run it on, and that the text-based executable of Unison is somewhere on the path (e.g. in /usr/bin/unison).

### INSTALLATION:

Download the Unison Menubar app and install on each Mac that you want to run it on.  (This can be any subset of the machines whose files you synchronize with Unison.)

### CONFIGURATION STEP 1 (CREATE DIRECTORY and CONFIGURATION FILE)

On each account/machine that you will run Unison Menubar on, create a directory (e.g. ~/.unison\_menubar) and a configuration file ~/.unison_menubar .  The first section in the configuration file should look like the following:

    [menubar]
    directory           = ~/.unison_menubar                 # directory u created
    terminal_notifier   = /opt/local/bin/terminal-notifier  # optional

(Add the latter line if you want additional status notifications sent via terminal-notifier, and you have [terminal-notifier](https://github.com/alloy/terminal-notifier) installed.  It's also available via macports.)

After that section, you should add a section for each Unison profile that you want to monitor or regularly synchronize.  For example, if on local machine a.example.com you want to run unison on profile "work" every 10 minutes, you would create a section in the configuration file on machine a.example.com as follows:

    [work]                            # the name of the profile (or any unique id)
    root = ~                          # the root directory of this unison profile
    command = /usr/bin/unison work    # the command to run unison on this profile
    delay = 600                       # run unison every 10 minutes (600 seconds)
    
If you want to use Unison Menubar to _monitor_ that profile on a remote machine b.example.com (but to run Unison on that profile only on request), then on the _remote machine_ b.example.com, you would also run Unison Menubar, and in the configuration file (in addition to the [menubar] section) you would add a section as follows:

    [work]                            # the same name 
    root = ~                          # root directory of profile on this machine
    command = ssh a.example.com unison work  # assuming you have ssh keys set up

The "command = ssh a.example.com unison work" is just there in case, while you are on b.example.com, you want to tell Unison Menubar to synchronize the work profile.  The given command will do that by running Unison remotely on a.example.com (the output will be captured by Unison Menubar and used to determine the status).  Since there is no "delay" option in this section, Unison Menubar will do this only be explicit request.

You can add additional sections for every profile you want to monitor.  

### CONFIGURATION STEP 2 (ADD LINES TO UNISON .prf FILE)

Recall the ~/.unison_menubar directory (or equivalent) that you created above.  Whenever Unison Menubar invokes Unison on a profile for you, it records the output in this directory, in a file such as work.log (where "work" is the profile name).  It uses these files to determine the status of the last execution for each profile.  Unison Menubar relies on Unison to synchronize the files in this directory (across the machines that you run Unison Menubar on).  This allows Unison Menubar running on one machine (e.g. b.example.com) to report the status of the Unison executions that were invoked by Unison Menubar running on a remote machine (e.g. a.example.com).

To make this work, you need to have Unison synchronize this directory across all of the machines.  To do this, you can add the following lines to the profiles that are synchronized (assuming you created the .unison_menubar directory in the root of the profile):

    path = .unison_menubar
    preferpartial = BelowPath .unison_menubar -> newer

The first option makes sure that when Unison runs for this profile, it synchronizes the directory.  The second option is necessary to resolve conflicts in favor of the more recent runs.

### RUNNING Unison Menubar

Run it as an ordinary standalone app.  (Or, for development, you can also run the python source directly, if you have the dependencies installed, e.g. py27-pyobjc-cocoa).

If all goes as planned, you will see a "U" icon appear in the menubar.  Clicking on the icon will bring up a menu with commands, and an entry for each profile in the configuration file.  The icon will change color to indicate status (gray for disconnected, red for errors, green for pending sync).  If there are errors for a particular profile, they will be shown in the submenu for the profile.
