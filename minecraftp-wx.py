#!/usr/bin/env python

import os, sys, urllib, subprocess, platform, random, threading
from datetime import datetime
import wx
from deps import *

# -------------------------------------------------------
# - mbilker modified version of Minecraft Portable 2.7 --
# - Original by NotTarts                               --
# - Minecraft logging to stdout thanks to MCP          --
# -------------------------------------------------------

# -------------
# - wxPython --
# -------------

class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        global logger
        wx.Frame.__init__(self, parent, title=title, size=(500,500))
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(EVT_LOG, self.OnLog)
        logger = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.Show(True)
        Minecraft(self).start()

    def OnClose(self, event):
        event.Veto()

    def OnLog(self, evt):
        logger.AppendText(unicode(evt.GetValue() + "\n"))

myEVT_LOG = wx.NewEventType()
EVT_LOG = wx.PyEventBinder(myEVT_LOG, 1)
class LogEvent(wx.PyCommandEvent):
    """Event to log to window"""
    def __init__(self, etype, eid, value=None):
        """Creates the event object"""
        wx.PyCommandEvent.__init__(self, etype, eid)
        self._value = value

    def GetValue(self):
        """Returns the value from the event.
        @return: the value of this event
        """
        return self._value

# ---------------------
# - Minecraft Thread --
# ---------------------

class Minecraft(threading.Thread):
    def __init__(self, parent):
        """
        @param parent: The gui object that should recieve the value
        """
        threading.Thread.__init__(self)
        self._parent = parent

    def run(self):
        launcher.launch(user, config, self._parent)
        frame.Destroy()

# --------------------------
# - Classes and functions --
# --------------------------

class argParser():
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-version', help='Choose a different version of minecraft', default='notchosen')
        self.parser.add_argument('-logwindow', help='Choose whether to display the wxPython window', default=False)
        self.parser.add_argument('-server', help='Run the vanilla minecraft server', default=False)
        self.version = self.parser.parse_known_args()[0].version
        self.logwindow = self.parser.parse_known_args()[0].logwindow
        self.server = self.parser.parse_known_args()[0].server

class mcpLog():
    def __init__(self, filename):
        # Creating the initial log file/erasing old log
        self.logFilename = filename
        self.logObj = open(self.logFilename,'w')
        self.logObj.close()

    def write(self, content):
        # Appending to the log
        self.logObj = open(self.logFilename,'a')
        self.logObj.write(content)
        sys.stdout.write(content)
        self.logObj.close()

class mcpConfig():
    def __init__(self, filename):
        # We store the config spec in temp
        randnum = str(random.randint(10000, 99999))
        if platform.system() == 'Windows':
            self.configSpec = os.getenv('TEMP') + '\mcp_configspec' + randnum + '.ini'
        elif platform.system() == 'Darwin':
            self.configSpec = '/private/tmp/mcp_configspec' + randnum + '.ini'

        # The config spec is basically the config file 'template'
        specfile = open(self.configSpec,'w')
        specFileData = '''\
[MCPSettings]
enableLog = boolean(default=True)
dumpDebugInfo = boolean(default=True)
javaFolder = string(default="")
version = string(default="1.2.5")

[AutoLogin]
username = string(default="")
password = string(default="")
server = string(default="")
'''
        specfile.write(specFileData)
        specfile.close()

        # Load config and make sure it matches the spec
        self.config = ConfigObj(filename, configspec=self.configSpec)
        self.config.validate(Validator(), copy=True)

        # Setting class vars
        self.enableLog = self.config['MCPSettings']['enableLog']
        self.dumpDebugInfo = self.config['MCPSettings']['dumpDebugInfo']
        self.version = self.config['MCPSettings']['version']
        self.javaFolder = self.config['MCPSettings']['javaFolder']

        self.username = self.config['AutoLogin']['username']
        self.password = self.config['AutoLogin']['password']
        self.server = self.config['AutoLogin']['server']

        self.config.write()

    def eraseUserData(self):
        # Erasing the username, password, etc from config
        self.config['AutoLogin']['username'] = ""
        self.config['AutoLogin']['password'] = ""
        self.config.write()

class mcpUserData():
    def __init__(self, config, userFile, key):

        log.write('Searching for login information...\n')

        if config.username and config.password:
            # User info found in config
            log.write('- Found in config, erasing... ')
            self.username = config.username
            self.password = config.password
            config.eraseUserData()
            log.write('done.\n')

            # Create our autologin file using encrypted data
            log.write('- Encrypting user data and saving to file... ')
            encryptedData = key.encrypt('{}/{}'.format(self.username, self.password))
            fileObject = open(userFile, 'w')
            fileObject.write(encryptedData)
            fileObject.close()
            log.write('done.\n')

        elif os.path.isfile(userFile):
            # Autologin file already exists, so we decrypt the data in it
            # and store it in the class vars
            log.write('- Found autologin file.\n')
            log.write('- Decrypting user data... ')
            fileObject = open(userFile, 'r')
            decryptedData = key.decrypt(fileObject.read())
            fileObject.close()

            self.username = decryptedData.rsplit('/')[0]
            self.password = decryptedData.rsplit('/')[1]

            log.write('done.\n')

        else:
            log.write('- No login information found\n')
            self.username = None
            self.password = None

        log.write('\n')

class mcpLauncher():
    def __init__(self, filename, url):
        log.write('Launching Minecraft...\n')

        if not os.path.isdir(os.path.split(filename)[0]): os.mkdir(os.path.split(filename)[0])     
        if not os.path.exists(filename):
            log.write('- Launcher not found, downloading... ')
            urllib.urlretrieve(url, filename)
            log.write('done.\n')

        self.launcherJar = filename


    def findJava(self, directories):
        log.write('- Searching for Java binaries... ')
        # Going through every directory in the list to find javaw.exe
        for directory in directories:
            if platform.system() == 'Windows':
                binFile = findFile('javaw.exe', directory)
            elif platform.system() == 'Darwin':
                binFile = findFile('java', directory)
            if binFile:
                self.javaBin = binFile
                log.write('done.\n')
                log.write('- Found Java at {}.\n'.format(os.path.realpath(self.javaBin)))
                return
            else: self.javaBin = None

        if not self.javaBin:
            # Java is needed, so if it's not found the app exits
            log.write('\nError: Could not find Java binaries.')
            sys.exit(1)

    def launch(self, user, config, wxparent):
        if user.username and user.password:
            log.write('- Using autologin data for username and password\n')
        else: config.server = None # We can't use the server info without the username/password
        if config.server: log.write('- Autologin server found: {}\n'.format(config.server))

        javaArguments = [os.path.realpath(self.javaBin)] + ['-Xms512M', '-Xmx1024M', '-cp', self.launcherJar, 'net.minecraft.LauncherFrame', user.username, user.password, config.server]
        javaArguments = filter(None, javaArguments) # Remove any empty values (added from config, etc)
#        subprocess.call(javaArguments)
        proc = subprocess.Popen(javaArguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log.write('- Log of Minecraft\n')
        msgs = []
        while True:
            o = proc.stdout.readline()
            returnvalue = proc.poll()
            if o == '' and returnvalue is not None:
                break
            if o != '':
                log.write(o.strip() + '\n')
                if arguments.logwindow == True:
                    evt = LogEvent(myEVT_LOG, -1, o.strip())
                    wx.PostEvent(wxparent, evt)

        if returnvalue != 0:
            for msg in msgs:
                log.write(msg)
        else:
            for msg in msgs:
                log.write(msg)

class mcpServer():
    def __init__(self, filename, url):

        self.serverDir = os.path.split(filename)[0]

        if not os.path.isdir(self.serverDir): os.mkdir(self.serverDir)    
        if not os.path.exists(filename):
            log.write('- Server not found, downloading... ')
            urllib.urlretrieve(url, filename)
            log.write('done.\n')

        self.serverJar = filename

    def launch(self, config, launcher):
        arguments = [os.path.realpath(launcher.javaBin)] + ['-jar', os.path.realpath(self.serverJar)]
        arguments = filter(None, arguments) # Remove any empty values (added from config, etc)
        os.chdir(self.serverDir)
        subprocess.call(arguments)

def checkForExternal():
    if not len(sys.argv) < 2 and not sys.argv[1] == '-server':
        # If an application is dropped onto minecraftp.exe, we run it from here as
        # this will cause it to use the .minecraft folder in mcp_data rather than
        # the folder in AppData
        log.write('External program detected, launching...')
        subprocess.call(sys.argv[1])
        sys.exit(0)

def findFile(filename, directory):
    for root, dirs, files in os.walk(directory):
        for name in files:
            if name == filename:
                return os.path.join(root, name)

def dumpDebug():
    debug = open(debugFile,'w')
    debug.write('Working directory: ' + os.path.realpath(currentDir) + '\n')
    debug.write('Data directory: ' + os.path.realpath(dataDir) + '\n')
    debug.write('Minecraft directory: ' + os.path.realpath(versionDir) + '\n')
    debug.write('Java Portable folder: ' + os.path.realpath(javaFolder) + '\n')
    debug.write('ConfigSpec File: ' + configSpec + '\n')
    debug.write('Launcher Jar: ' + os.path.realpath(launcherJar) + '\n')
    debug.close()
    return

# ---------------------------------------
# - Setting variables/creating folders --
# ---------------------------------------

if hasattr(sys, 'frozen'):
    if platform.system() == 'Windows':
        currentDir = os.path.dirname(sys.executable)
    elif platform.system() == 'Darwin':
        currentDir = os.path.normpath(os.path.join(sys.path[0], '..', '..', '..'))
else:
    currentDir = sys.path[0]

if platform.system() == 'Windows':
    os.system("title Minecraft Portable")

key = triple_des('ydK5203s5485MxB02ky31kWl', CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)

dataDir = os.path.join(currentDir, 'mcp_data')
launcherDir = os.path.join(dataDir, 'launcher') # Place to save the launcher (minecraft.jar)
serverDir = os.path.join(dataDir, 'server') # Place to save the server (minecraft_server.jar)

launcherFile = os.path.join(launcherDir, 'minecraft.jar') 
launcherUrl = 'https://s3.amazonaws.com/MinecraftDownload/launcher/minecraft.jar'

serverFile = os.path.join(serverDir, 'minecraft_server.jar') 
serverUrl = 'https://s3.amazonaws.com/MinecraftDownload/launcher/minecraft_server.jar'

javaFolder = dataDir + '/java/bin'

configFile = os.path.join(dataDir, 'config.ini')
userFile = os.path.join(dataDir, 'autologin')
logFile = os.path.join(dataDir, 'mcp_log.log')
MClogFile = os.path.join(dataDir, 'minecraft_log.log')
debugFile = os.path.join(dataDir, 'debug.txt')

if not os.path.isdir(dataDir): os.mkdir(dataDir)
if not os.path.isdir(dataDir + '/version'): os.mkdir(dataDir + '/version')
if not os.path.isdir(launcherDir): os.mkdir(launcherDir)
        
# -------------------
# - Actual program --
# -------------------

arguments = argParser()
config = mcpConfig(configFile)
log = mcpLog(logFile)

log.write('Minecraft Portable 2.7.1\nby NotTarts (mbilker modified version)\n\nStarted at {}\nData directory: {}\n\n'.format(datetime.now(), os.path.realpath(dataDir)))

if arguments.version != 'notchosen':
    version = arguments.version
    log.write('Changed Minecraft version to %s\n' %(version))

versionDir = os.path.join(dataDir, 'version', config.version)
log.write(config.version + ' Minecraft version used\n')
if not os.path.isdir(versionDir): os.mkdir(versionDir)

libraryDir = os.path.join(versionDir, 'Library')
supportDir = os.path.join(libraryDir, 'Application Support')
storeLink = os.path.join(supportDir, 'minecraft')
storeDir = os.path.join(versionDir, '.minecraft')

if not os.path.isdir(libraryDir): os.mkdir(libraryDir)
if not os.path.isdir(supportDir): os.mkdir(supportDir)
if not os.path.isdir(storeDir): os.mkdir(storeDir)
if not os.path.islink(storeLink): os.symlink(storeDir, storeLink)

if platform.system() == 'Windows':
    os.putenv('APPDATA',versionDir)
elif platform.system() == 'Darwin':
    os.putenv('HOME',versionDir)

if not platform.system() == 'Darwin':
    checkForExternal()

user = mcpUserData(config, userFile, key) # Load our user data from wherever, if it exists
launcher = mcpLauncher(launcherFile, launcherUrl) # Downloading launcher

systemJava = []
if platform.system() == 'Windows':
    systemJava.append(os.path.join(str(os.getenv('ProgramW6432')), 'Java'), os.path.join(str(os.getenv('ProgramFiles(x86)')), 'Java'))
elif platform.system() == 'Darwin':
    systemJava.append('/usr/bin')

launcher.findJava([config.javaFolder, dataDir] + systemJava)

if arguments.server:
    server = mcpServer(serverFile, serverUrl) # Downloading server
    server.launch(config, launcher) # Launch Minecraft server!

if arguments.logwindow == True:
    app = wx.App(False)
    frame = MainWindow(None, "Minecraft Log")
    app.MainLoop()
else:
    launcher.launch(user, config, None) # Launch Minecraft!
#launcher.launch(user, config, None) # Launch Minecraft!

if os.path.isfile(config.configSpec): os.remove(config.configSpec)

log.write('\nProcess finished.\n')
