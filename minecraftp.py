#!/usr/bin/env python

import os,sys, urllib, subprocess, platform, random, wx, threading
import deps

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
        self.Bind(EVT_COUNT, self.OnCount)
        logger = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.Show(True)
        Minecraft(self).start()

    def OnClose(self, event):
        event.Veto()

    def OnCount(self, evt):
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
        launchMinecraft(self._parent)
        frame.Destroy()

# --------------------------
# - Classes and functions --
# --------------------------

class argParser():
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-version', help='Choose a different version of minecraft', default='notchosen')
        self.parser.add_argument('-logwindow', help='Choose whether to display the wxPython window', default='yes')
        self.version = self.parser.parse_args().version
        self.logwindow = self.parser.parse_args().logwindow

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
        self.logObj.close()

class mcpConfig():
    def __init__(self, filename):
        # We store the config spec in temp
        self.configSpec = os.getenv('TEMP') + '\mcp_configspec.ini'

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
        self.enableLog = config['MCPSettings']['enableLog']
        self.dumpDebugInfo = config['MCPSettings']['dumpDebugInfo']
        self.version = config['MCPSettings']['version']
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
            binFile = findFile('javaw.exe', directory)
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

    def launch(self, user, config):       
        if user.username and user.password:
            log.write('- Using autologin data for username and password\n')
        else: config.server = None # We can't use the server info without the username/password
        if config.server: log.write('- Autologin server found: {}\n'.format(config.server))

        arguments = [os.path.realpath(self.javaBin)] + config.javaArgs.split() + ['-cp', self.launcherJar, 'net.minecraft.LauncherFrame', user.username, user.password, config.server]
        arguments = filter(None, arguments) # Remove any empty values (added from config, etc)
        
        subprocess.call(arguments)

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
        arguments = [os.path.realpath(launcher.javaBin)] + config.javaArgs.split() + ['-jar', os.path.realpath(self.serverJar)]
        arguments = filter(None, arguments) # Remove any empty values (added from config, etc)
        os.chdir(self.serverDir)
        subprocess.call(arguments)
        msgs = []
        while True:
            o = proc.stdout.readline()
            returnvalue = proc.poll()
            if o == '' and returnvalue is not None:
                break
            if o != '':
                writeLog(o.strip())
                if args.logwindow == 'yes':
                    evt = CountEvent(myEVT_LOG, -1, o.strip())
                    wx.PostEvent(parent, evt)

        if returnvalue != 0:
            for msg in msgs:
                writeLog(msg)
        else:
            for msg in msgs:
                writeLog(msg)

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

#----------------------------------------------------
#- Functions
#----------------------------------------------------

def readConfig():
    writeConfigSpec()

    global enableLog
    global dumpDebugInfo
    global javaFolder
    global username
    global password
    global server
    global config
    global launcherJar
    global launcherClass
    global version
    global versionDir

    username = ''
    password = ''
    server = ''

    config = ConfigObj(configFile, configspec=configSpec)
    validator = Validator()
    config.validate(validator, copy=True)

    enableLog = config['MCPSettings']['enableLog']
    dumpDebugInfo = config['MCPSettings']['dumpDebugInfo']
    version = config['MCPSettings']['version']

    startLog()

    writeLog('Minecraft Portable 2.6')
    writeLog('by NotTarts')
    writeLog('mbilker modified version')
    writeLog('')

    writeLog('Standard Minecraft Launcher being used')
    launcherJar = launcherDir + '/minecraft.jar'
    launcherClass = 'net.minecraft.LauncherFrame'

    if args.version != 'notchosen':
        version = args.version
        writeLog('Changed Minecraft version to %s' %(version))

    versionDir = dataDir + '/version/' + version
    if not os.path.isdir(versionDir): os.mkdir(versionDir)
    writeLog(version + ' Minecraft version used')
    writeLog('')

    if platform.system() == 'Windows':
        os.putenv('APPDATA',versionDir)
    elif platform.system() == 'Darwin':
        os.putenv('HOME',versionDir)

    if os.path.isfile(config['MCPSettings']['javaFolder'] + '/javaw.exe'):
        javaFolder = config['MCPSettings']['javaFolder']
        writeLog('Custom Java Portable binary path found.')
        writeLog('')
    else:
        config['MCPSettings']['javaFolder'] = 'default'

    if not config['AutoLogin']['server'] == 'none':
        if not len(config['AutoLogin']['server']) < 6:
            server = config['AutoLogin']['server']
        else: config['AutoLogin']['server'] = 'none'

    if len(config['AutoLogin']['username']) < 3: config['AutoLogin']['username'] = 'none'
    if len(config['AutoLogin']['password']) < 3: config['AutoLogin']['password'] = 'none'

    readUserData()
    if dumpDebugInfo == True:
        dumpDebug()

    config.write()
    return

def launchMinecraft(parent):
    writeLog('Launching Minecraft...')

    arguments = ['']

    if not username == '':
        arguments = [username, password]
        writeLog('- Using autologin data for username and password.')
    if not server == '':
        arguments = [username, password, server]
        writeLog('- Auto-login server found: ' + server)

    if os.path.isdir(javaFolder):
        writeLog('- Java Portable binaries discovered.')
        if platform.system() == 'Windows':
            proc = subprocess.Popen([os.path.realpath(javaFolder + '/javaw.exe'),'-Xms512M','-Xmx512M','-cp',launcherJar,launcherClass] + arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        elif platform.system() == 'Darwin':
            proc = subprocess.Popen(['/usr/bin/java','-Xms512M','-Xmx512M','-cp',launcherJar,launcherClass] + arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        writeLog('- Log of Minecraft.')

        msgs = []
        while True:
            o = proc.stdout.readline()
            returnvalue = proc.poll()
            if o == '' and returnvalue is not None:
                break
            if o != '':
                writeLog(o.strip())
                if args.logwindow == 'yes':
                    evt = CountEvent(myEVT_LOG, -1, o.strip())
                    wx.PostEvent(parent, evt)

        if returnvalue != 0:
            for msg in msgs:
                writeLog(msg)
        else:
            for msg in msgs:
                writeLog(msg)

    else:
        writeLog('- No Java Portable binaries discovered.')
        subprocess.call([launcherExe] + arguments)

    writeLog('- Done.')
    return

# ---------------------------------------
# - Setting variables/creating folders --
# ---------------------------------------

if hasattr(sys, 'frozen'):
    currentDir = os.path.dirname(sys.executable)
else:
    currentDir = sys.path[0]

if platform.system() == 'Windows':
    os.system("title Minecraft Portable")

key = triple_des('ydK5203s5485MxB02ky31kWl',CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)

dataDir = os.path.join(currentDir, 'mcp_data')
launcherDir = os.path.join(dataDir, 'launcher') # Place to save the launcher (minecraft.jar)
serverDir = os.path.join(dataDir, 'server') # Place to save the server (minecraft_server.jar)

launcherFile = os.path.join(launcherDir, 'minecraft.jar') 
launcherUrl = 'https://s3.amazonaws.com/MinecraftDownload/launcher/minecraft.jar'

serverFile = os.path.join(serverDir, 'minecraft_server.jar') 
serverUrl = 'https://s3.amazonaws.com/MinecraftDownload/launcher/minecraft_server.jar'

javaFolder = dataDir + '/java/bin'

configFile = os.path.join(dataDir, '/config.ini')
logFile = os.path.join(dataDir, '/mcp_log.log')
MClogFile = os.path.join(dataDir, '/minecraft_log.log')
debugFile = os.path.join(dataDir, '/debug.txt')

if not os.path.isdir(dataDir): os.mkdir(dataDir)
if not os.path.isdir(dataDir + '/version'): os.mkdir(dataDir + '/version')
if not os.path.isdir(launcherDir): os.mkdir(launcherDir)
        
# -------------------
# - Actual program --
# -------------------

arguments = argParser()
config = mcpConfig(configFile)
log = mcpLog(logFile)

if arguments.version != 'notchosen':
    version = args.version
    log.write('Changed Minecraft version to %s\n' %(version))

versionDir = os.path.join(dataDir, '/version/', version)
if not os.path.isdir(versionDir): os.mkdir(versionDir)
log.write(version + ' Minecraft version used\n')

if platform.system() == 'Windows':
    os.putenv('APPDATA',versionDir)
elif platform.system() == 'Darwin':
    os.putenv('HOME',versionDir)

log.write('Minecraft Portable 2.7.1\nby NotTarts (mbilker modified version)\n\nStarted at {}\nData directory: {}\n\n'.format(datetime.now(), os.path.realpath(dataDir)))

checkForExternal()

user = mcpUserData(config, userFile, key) # Load our user data from wherever, if it exists
launcher = mcpLauncher(launcherFile, launcherUrl) # Downloading launcher

systemJava = []
if platform.system() == 'Windows':
    systemJava.append(os.path.join(str(os.getenv('ProgramW6432')), 'Java'), os.path.join(str(os.getenv('ProgramFiles(x86)'))))
elif platform.system() == 'Darwin':
    systemJava.append('/usr/bin/java')

launcher.findJava([config.javaFolder, dataDir, systemJava, 'Java')])

if arguments.server:
    server = mcpServer(serverFile, serverUrl) # Downloading server
    server.launch(config, launcher) # Launch Minecraft server!
else: launcher.launch(user, config) # Launch Minecraft!

if arguments.logwindow == 'yes':
    app = wx.App(False)
    frame = MainWindow(None, "Minecraft Log")
    app.MainLoop()
else:
    launchMinecraft('no')

if os.path.isfile(configSpec): os.remove(configSpec)

log.write('\nProcess finished.')
