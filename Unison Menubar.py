#!/usr/bin/env python2.7

import os, datetime, glob, threading, Queue

from AppKit import *
## NSObject, NSApplication, NSStatusBar, NSVariableStatusItemLength,
## NSImage, NSMenu, NSMenuItem, NSDate, NSTimer, NSRunLoop, NSDefaultRunLoopMode
#import objc
#from Foundation import *
from PyObjCTools import AppHelper

RESOURCEDIR = os.environ.get('RESOURCEPATH', '/Users/neal/hacking/unison_menubar') + "/"

class config:
    import ConfigParser
    _i = {"UNISONLOCALHOSTNAME": os.getenv("UNISONLOCALHOSTNAME") or os.getenv("HOST")}
    _c = ConfigParser.SafeConfigParser()
    _c.read([RESOURCEDIR + "unison_menubar.ini", os.path.expanduser("~/.unison_menubar.ini")])
config.profiles = {section : {key :
                                os.path.expanduser(str(config._c.get(section, key, config._i)))
                              for key in config._c.options(section)}
                   for section in config._c.sections()}
config.menubar = config.profiles['menubar']
del config.profiles['menubar']

DEBUG_LEVEL = int(config.menubar["debug_level"])

IMAGES = {}
_imagedir = os.environ.get('RESOURCEPATH', '/Users/neal/hacking/unison_menubar') + "/images/"
for s in [os.path.basename(x)[:-4] for x in glob.glob(_imagedir + "*.png")]:
    IMAGES[s] = NSImage.alloc().initByReferencingFile_(_imagedir + s + ".png")
    IMAGES[s].setScalesWhenResized_(True)
    IMAGES[s].setSize_((15, 15))
del _imagedir

#### debugging decorator
if DEBUG_LEVEL:
    import pdb, sys
    import functools
    def debug_(f):
        @functools.wraps(f)
        def wrapper(self, notifications):
            try:       return f(self, notifications)
            except:    pdb.post_mortem(sys.exc_info()[2])
        return wrapper
else:
    def debug_(f):  return f
### end debugging decorator

TIME_FORMAT = "%H:%M:%S.%f on %d %b %Y"

def parse_time(time):
    return datetime.datetime.strptime(" ".join(time), TIME_FORMAT)

def parse_output(output):
    time = None
    errors = []
    completed = []
    disconnected = False
    for line in output.split("\n"):
        if not time and "propagating changes at" in line:
            time = _parse_time(line.split()[-5:])
        elif any(line.startswith(x) for x in ('[CONFLICT]', '[ERROR]')):
            errors.append(line.split(" ", 2)[2].strip())
        elif line.startswith("[END]"):
            i = 3 if line.startswith("[END] Updating file") else 2
            completed.append(line.split(" ", i)[i].strip())
        elif "<-?->" in line:
            line = line[line.find("<-?->")+6:]
            i = 2 if line.startswith("new file") else 1
            errors.append(line.split(None, i)[i].strip())
        elif "Lost connection with the server" in line \
          or "ssh: Could not resolve" in line:
            disconnected = True
        elif "Fatal error:" in line:
            errors.append(line)
            
    return dict(time=time,
                errors=sorted(set(errors)),
                completed=sorted(set(completed)),
                disconnected=disconnected)

def ago(time):
    seconds_old = int((datetime.datetime.now() - time).total_seconds())
    minutes_old = int(seconds_old/60)
    hours_old = int(minutes_old/60)
    days_old = int(hours_old/24)
    if days_old >= 2:
        age = str(days_old) + " days ago"
    elif hours_old >= 2:
        age = str(hours_old) + " hours ago"
    elif minutes_old >= 1:
        age = "1 minute ago" if minutes_old == 1 else str(minutes_old) + " minutes ago"
    else:
        age = str(seconds_old) + " seconds ago"
    return age

class Profile:
    def __init__(self, profile, menu = None):
        self.profile  = profile
        self.config   = config.profiles[profile]
        self.filename = config.menubar['directory'] + '/' + profile + ".log"
        self.status = dict(time=datetime.datetime.now(), state='unknown')

        self.last_update_time = None
        self.last_run_time = datetime.datetime.now()
        
        self.input_q, self.output_q = Queue.Queue(), Queue.Queue()
        def slave():
            while True:
                self.output_q.put(self.input_q.get()())
        self.slave = threading.Thread(target=slave, args = ())
        self.slave.daemon = True
        self.slave.start()
        self.slave_busy = False

    def _check_output_q(self):
        try:
            result = self.output_q.get_nowait()
            self.slave_busy = False
            self.last_run_time = datetime.datetime.now()
            return result
        except Queue.Empty:
            return None

    def runnable(self):
        self._check_output_q()
        return not self.slave_busy
    
    def run(self, options = ''):
        if not self.runnable(): return
        self.input_q.put(lambda: self._run(options))
        self.slave_busy = True
        self.last_run_time = datetime.datetime.now()
        
    def _run(self, options = ''):
        executable  = self.config['command']
        cmd = executable + " -ui text -batch " + options
        print "#RUN", cmd
        process = subprocess.Popen([cmd], shell=True, stdin=open("/dev/null"),
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                bufsize = 1)
        #output = process.stdout.read()
        if DEBUG_LEVEL:
            print "#process", process.pid
        lines = []
        for line in process.stdout:
             if DEBUG_LEVEL: print "#", line,
             lines.append(line)
        output = "".join(lines)
        print "#RUN DONE"
        retcode = process.wait()
        print "#END RUN.  retcode", retcode
        with open(self.filename, "w") as f:
            print >>f, "[COMMAND]", cmd, "\n", output, "[RETURN]", retcode

    def status_update(self):
        state = None
        errors = []
        time = self.status['time']
        self._check_output_q()
        if self.slave_busy:
            if self.status['state'] != 'pending':
                self.status = dict(state='pending', time=datetime.datetime.now())
                time = datetime.datetime.now()
            summary = "sync started %s" % (ago(time))
        elif not os.path.isfile(self.filename):
            if self.status['state'] != 'unknown':
                self.status = dict(state='unknown', time=datetime.datetime.now())
                time = datetime.datetime.now()
            summary = "unknown state since %s" % (ago(time))
        else:
            time = datetime.datetime.fromtimestamp(os.path.getmtime(self.filename))
            changed = time != self.last_update_time
            if changed:
                self.last_update_time = time
                with open(self.filename) as f: output = f.read()
                self.status = parse_output(output)
                self.status['time'] = self.status['time'] or time
                self.last_run_time = min(time, self.last_run_time or time)

            errors = self.status.get('errors', [])
            time = ago(self.status['time'])
            if errors:
                state = 'errors'
                summary = "%d errors %s" % (len(errors), time)
            elif self.status.get('disconnected'):
                state = 'disconnected'
                summary = "unable to connect %s" % (time)
            else:
                state = 'good'
                summary = "full sync %s" % (time)
            self.status['state'] = state

            if changed:
                def shorten(x, n = 37):
                    if len(x) < n: return x
                    a = int(.4*n)-2
                    b = len(x)-int(.6*n)+1
                    i = x.rfind("/", 0, a)
                    j = x.find("/", b)
                    if i < 3: i = a
                    if j < 0 or j >= len(x)-5: j = b
                    return x[:i+1]+"..."+x[j:]

                if state == 'good':
                    mac_notifier('', ID="Unison ERRORS " + self.profile)

                completed = self.status.get("completed", [])
                completed = [f for f in completed
                             if os.path.abspath(os.path.dirname(self.config['root'] + "/" + f))
                             != os.path.abspath(config.menubar['directory'])]
                if completed:
                    mac_notifier("\n".join(shorten(x) for x in completed),
                                 "synced from " + self.profile)
                if errors:
                    mac_notifier("\n".join(shorten(x) for x in errors),
                                 "Unison errors from " + self.profile,
                                 ID="Unison ERRORS " + self.profile)
        
        return [summary] + errors

menuitem_actions = {}

def new_menu_item(title, action = None, tooltip = None, enabled = None):
    global menuitem_actions
    if enabled == None: enabled = bool(action)
    if action and type(action) == str:
        menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, '')
    elif action:
        menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, 'act:', '')
        menuitem_actions[menuitem] = action
    else:
        menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, '', '')
    if tooltip: menuitem.setToolTip_(tooltip)
    menuitem.setEnabled_(enabled)
    return menuitem
            
def forget_menu_item_action(menuitem):
    global menuitem_actions
    if menuitem in menuitem_actions:
        del menuitem_actions[menuitem]

def add_menu_item(menu, *args, **kwargs):
    menuitem = new_menu_item(*args, **kwargs)
    menu.addItem_(menuitem)
    return menuitem

class ReportMenu:
    def __init__(self, menu, profile):
        self.menu = menu
        self.items = set()
        self.profile = profile

    def _add(self, title):
        filename = self.profile.config['root'] + '/' + title
        action = os.path.exists(filename) and (lambda: os.system("open -R '%s'" % filename))
        i = new_menu_item(title, action = action)
        self.menu.addItem_(i)
        self.items.add(i)

    def update(self, titles):
        for i in self.items:
            forget_menu_item_action(i)
            self.menu.removeItem_(i)
        self.items = set()
        for t in titles:
            self._add(t)

class ActiveMenu:
    def __init__(self, menu):
        self.menu = menu
        self.predicates = {}

    def add(self, i, predicate):
        self.menu.addItem_(i)
        self.predicates[i] = predicate
        i.setEnabled_(predicate())

    def update(self):
        for i,p in self.predicates.items():
            i.setEnabled_(p())

class Timer(NSObject):
    @debug_
    def applicationDidFinishLaunching_(self, notification):
        self.menubarItem = \
            NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.menubarItem.setImage_(IMAGES['unknown'])
        self.menubarItem.setHighlightMode_(1)
        self.menubarItem.setToolTip_('Unison menubar')

        self.menu = NSMenu.alloc().init()
        self.menu.setAutoenablesItems_(False)
        self.menubarItem.setMenu_(self.menu)
            
        self.actions = {}
        
        add_menu_item(self.menu, 'Sync manually...',
                      lambda: os.system("open -a Unison"),
                      'Open Unison to do a local manual sync.\n'\
                      'Use this to resolve local conflicts manually.')

        add_menu_item(self.menu, 'Quit', 'terminate:')

        # separator
        self.menu.addItem_(NSMenuItem.separatorItem())

        self.profiles = set(Profile(p) for p in config.profiles)

        for p in sorted(self.profiles, key = lambda p: p.profile):
            p.root_menuitem = add_menu_item(self.menu, p, enabled = True)
            p.submenu = NSMenu.alloc().init()
            p.submenu.setAutoenablesItems_(False)
            p.root_menuitem.setSubmenu_(p.submenu)
            p.report_menu = ReportMenu(p.submenu, p)
            p.active_menu = ActiveMenu(p.submenu)

            for x in [('Sync @' + p.profile, lambda p=p: p.run(),
                        'Do a full sync in the background now.'),
                      ('Force newer', lambda p=p: p.run("-prefer newer"),
                       'Do a full sync, resolving conflicts by taking newer files.'),
                      ('Force older', lambda p=p: p.run("-prefer older"),
                       'Do a full sync, resolving conflicts by taking older files.')]:

                p.active_menu.add(new_menu_item(*x),
                                  lambda p=p: not (p.status and p.status['state'] == 'pending'))

            p.active_menu.add(new_menu_item(
                                  'Show log...',
                                  lambda: os.system("open 'file://%s'" % p.filename),
                                  'Open the log file for the most recent sync.'),
                              lambda p=p: os.path.isfile(p.filename))
            # separator
            p.submenu.addItem_(NSMenuItem.separatorItem())

        self.updateStatus()

        # Get the timer going
        start_time = NSDate.date()
        self.timer = NSTimer.alloc().initWithFireDate_interval_target_selector_userInfo_repeats_(
            start_time, 10.0, self, 'tick:', None, True)
        NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, NSDefaultRunLoopMode)
        self.timer.fire()

    #@debug_
    def act_(self, notification):
        global menuitem_actions
        if notification in menuitem_actions:
            menuitem_actions[notification]()

    @debug_
    def tick_(self, notification):
        for p in self.profiles:
            delay = int(p.config['delay'])
            if 0 < delay < (datetime.datetime.now() - p.last_run_time).total_seconds():
                p.run()
        self.updateStatus()

    def updateStatus(self):
        for p in self.profiles:
            status = p.status_update()
            if not status: continue
            p.root_menuitem.setTitle_(p.profile + ": " + status[0])
            p.report_menu.update(status[1:])
            p.active_menu.update()
            
        states = set([p.status and p.status.get('state') for p in self.profiles])
        if 'pending' in states:
            state = 'pending'
        elif None in states or 'unknown' in states:
            state = 'unknown'
        elif 'errors' in states:
            state = 'errors'
        elif 'disconnected' in states:
            state = 'disconnected'
        elif states == set(['good']):
            state = 'good'
        else:
            state = 'unknown'

        self.menubarItem.setImage_(IMAGES[state])
            
### notifier

import subprocess

def mac_notifier(msg, title = 'Unison', ID = None):
    cmd = [config.menubar['terminal_notifier']]
    if not os.path.exists(*cmd): return
    if msg:
        cmd += ["-title", title]
        if ID: cmd.extend(['-group', ID])
        cmd.extend(['-message', msg])
    else:
        cmd += ["-remove", ID]
    try:
        notify = subprocess.Popen(cmd, stdout=open('/dev/null', 'w'), stderr=subprocess.STDOUT)
        retcode = notify.wait()
    except:
        e = sys.exc_info()[1]
        print "unexpected error running terminal-notifier ({})".format(e)
    if retcode != 0:
        print "unable to send notification! (retcode={})".format(retcode)
        print "notification:\n", msg or "(remove)"
    return retcode

if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    delegate = Timer.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()
  
