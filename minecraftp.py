#!/usr/bin/env python

import os,sys,urllib,subprocess,pickle,platform,random,wx,threading
from deps import *

#----------------------------------------------------
#- mbilker modified version of Minecraft Portable 2.7
#- Original by NotTarts
#- Minecraft logging to stdout thanks to MCP
#----------------------------------------------------

# --------------------------
# - Classes and functions --
# --------------------------

class argParser
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
        self.javaFolder = self.config['MCPSettings']['javaFolder']
        self.javaArgs = self.config['MCPSettings']['javaArgs']

        self.username = self.config['AutoLogin']['username']
        self.password = self.config['AutoLogin']['password']
        self.server = self.config['AutoLogin']['server']

        self.config.write()

    def eraseUserData(self):
        # Erasing the username, password, etc from config
        self.config['AutoLogin']['username'] = ""
        self.config['AutoLogin']['password'] = ""
        self.config.write()

#----------------------------------------------------
#- Functions
#----------------------------------------------------

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

def writeConfig():
    config = ConfigObj()
    config.filename = configFile

    MCPSettings = {
        'enableLog': 'True',
        'dumpDebugInfo': 'True',
        'javaFolder': 'default',
        'version': '1.2.5'
        }

    AutoLogin = {
        'username': 'none',
        'password': 'none',
        'server': 'none'
        }

    config['MCPSettings'] = MCPSettings
    config['AutoLogin'] = AutoLogin
    config.write()

    return

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


def readUserData():
    global userfile
    global username
    global password
    global server
    global config

    userfile = dataDir + '/autologin'

    if not os.path.isfile(userfile):
        if not config['AutoLogin']['password']=='none':
                if not config['AutoLogin']['username']=='none':
                        writeLog('Auto login data found in config.')
                        username = config['AutoLogin']['username']
                        password = config['AutoLogin']['password']

                        writeLog('- Encrypting login data...')
                        userdata = username + '/' + password
                        userdata = key.encrypt(userdata)
                        writeLog('- Erasing plain text user data in config...')
                        config['AutoLogin']['username'] = 'none'
                        config['AutoLogin']['password'] = 'none'
                        writeLog('- Creating autologin data file...')
                        userobject = open(userfile, 'w')
                        pickle.dump(userdata,userobject)
                        userobject.close()
                        writeLog('- Done')
                        writeLog('')

    writeLog('Searching for autologin data file...')
    if os.path.isfile(userfile):
        writeLog('- Data file discovered.')
        writeLog('- Opening and decrypting data...')
        userobject = open(userfile, 'r')
        userdata = pickle.load(userobject)
        userdata = key.decrypt(userdata)
        username = userdata.rsplit('/')[0]
        password = userdata.rsplit('/')[1]
        userobject.close()
        writeLog('- Done.')
        writeLog('')

    else:
        writeLog('- File not found')
        writeLog('')

    return

def downloadLauncher():
    if not os.path.exists(launcherExe):
        writeLog('Java launcher not found, downloading...')
        urllib.urlretrieve ('http://www.minecraft.net/download/Minecraft.exe', launcherExe)
    if not os.path.exists(launcherJar):
        writeLog('EXE launcher not found, downloading...')
        urllib.urlretrieve ('http://www.minecraft.net/download/minecraft.jar', launcherJar)
        writeLog('')

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

        msgs        = []
        while True:
            o = proc.stdout.readline()
            returnvalue = proc.poll()
            if o == '' and returnvalue is not None:
                break
            if o != '':
                writeLog(o.strip())
                if args.logwindow == 'yes':
                    evt = CountEvent(myEVT_COUNT, -1, o.strip())
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

#----------------------------------------------------
#- wxPython
#----------------------------------------------------

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

myEVT_COUNT = wx.NewEventType()
EVT_COUNT = wx.PyEventBinder(myEVT_COUNT, 1)
class CountEvent(wx.PyCommandEvent):
    """Event to signal that a count value is ready"""
    def __init__(self, etype, eid, value=None):
        """Creates the event object"""
        wx.PyCommandEvent.__init__(self, etype, eid)
        self._value = value

    def GetValue(self):
        """Returns the value from the event.
        @return: the value of this event

        """
        return self._value

#----------------------------------------------------
#- Minecraft
#----------------------------------------------------

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

dataDir = currentDir + '/mcp_data'

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

randnum = str(random.randint(10000, 99999))

if platform.system() == 'Windows':
    configSpec = os.getenv('TEMP') + '\mcp_configspec' + randnum + '.ini'
elif platform.system() == 'Darwin':
    configSpec = '/tmp/mcp_configspec' + randnum + '.ini'

if not os.path.isdir(dataDir): os.mkdir(dataDir)
if not os.path.isdir(dataDir + '/version'): os.mkdir(dataDir + '/version')
if not os.path.isdir(launcherDir): os.mkdir(launcherDir)
        
# -------------------
# - Actual program --
# -------------------

arguments = argParser()
config = mcpConfig(configFile)
log = mcpLog(logFile)

readConfig()

downloadLauncher()

if args.logwindow == 'yes':
    app = wx.App(False)
    frame = MainWindow(None, "Minecraft Log")
    app.MainLoop()
else:
    launchMinecraft('no')

if os.path.isfile(configSpec): os.remove(configSpec)

writeLog('')
writeLog('Process finished.')
