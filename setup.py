from setuptools import setup

# python setup.py py2app
# or
# python setup.py py2app -A

NAME = 'Unison Menubar'
SCRIPT = 'Unison Menubar.py'
VERSION = '0.1'
ID = 'unison_menubar'

DATA_FILES = ['images', 'unison_menubar.ini']

plist = dict(
     CFBundleName                = NAME,
     CFBundleShortVersionString  = ' '.join([NAME, VERSION]),
     CFBundleGetInfoString       = NAME,
     CFBundleExecutable          = NAME,
     CFBundleIdentifier          = 'name.young.neal.%s' % ID,
     LSUIElement                 = '1', #makes it not appear in cmd-tab task list etc.
)

app_data = dict(
    script=SCRIPT,
    plist=plist
   )

EXCLUDES = '''Crypto IPython ImageMode.pyc M2Crypto McIdasImagePlugin.pyc
MicImagePlugin.pyc MpegImagePlugin.pyc MspImagePlugin.pyc PIL PyQt4
PySide _dbus_bindings _dotblas _imaging _numpy _tikinter boto bzrlib
cairo config docutils email glib gntpsip gobject gtk h5py logilab
markupsafe matplotlib mercurial multiarray numpy plasTeX pycurl pydoc
pyglet pyside pytz pyzmq scipy simplejson sphinx spyderlib umatm
virtualenv_support zmq'''.split()

EXCLUDES = open("excludes").read().split()

setup(
   app = [app_data],
   options = dict(
       py2app = {
           "argv_emulation" : False,
           "resources" : DATA_FILES,
           "excludes" : EXCLUDES,
           "dylib_excludes" : EXCLUDES,
#           "semi_standalone" : True,
#           "includes" : [],
#           "packages" : [],
#           "site_packages" : False,
#           "debug_skip_macholib" : True,
        }
    ),
    setup_requires=["py2app"]
)

