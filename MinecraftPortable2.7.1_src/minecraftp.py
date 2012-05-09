import os, sys, urllib, subprocess, argparse
from datetime import datetime
from configobj import ConfigObj
from validate import Validator
from pyDes import *

# --------------------------
# - Classes and functions --
# --------------------------

class argParser():
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-server', action='store_true', default=False)
        self.server = self.parser.parse_args().server

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
javaFolder = string(default="")
javaArgs = string(default="")

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

        arguments = [os.path.realpath(self.javaBin)] + config.javaArgs.split() + ['-cp', self.launcherJar, 'net.minecraft.LauncherFrame',
                     user.username, user.password, config.server]
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
        arguments = [os.path.realpath(launcher.javaBin)] + config.javaArgs.split() + ['-jar', os.path.realpath(self.serverJar) ]
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

# ---------------------------------------
# - Setting variables/creating folders --
# ---------------------------------------

# Directory of app depends on whether it is a compiled exe or a script
if hasattr(sys, 'frozen'):
    currentDir = os.path.dirname(sys.executable)
else:
    currentDir = sys.path[0]

# Creating our encryption function, key must be 24 characters
key = triple_des('C4Ew6ep49w7PacHAtRepHA6r',CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)

dataDir = os.path.join(currentDir, 'mcp_data')
launcherDir = os.path.join(dataDir, 'launcher') # Place to save the launcher (minecraft.jar)
serverDir = os.path.join(dataDir, 'server') # Place to save the server (minecraft_server.jar)
os.putenv('APPDATA',dataDir) # Changing AppData locally so Minecraft/external applications store it here

launcherFile = os.path.join(launcherDir, 'minecraft.jar') 
launcherUrl = 'https://s3.amazonaws.com/MinecraftDownload/launcher/minecraft.jar'

serverFile = os.path.join(serverDir, 'minecraft_server.jar') 
serverUrl = 'https://s3.amazonaws.com/MinecraftDownload/launcher/minecraft_server.jar'

configFile = os.path.join(dataDir, 'config.ini')
userFile = os.path.join(dataDir, 'autologin')
logFile = os.path.join(dataDir, 'mcp_log.log')

if not os.path.isdir(dataDir): os.mkdir(dataDir)


# -------------------
# - Actual program --
# -------------------

arguments = argParser()
config = mcpConfig(configFile)
log = mcpLog(logFile)

# Write credits, date, etc
log.write('Minecraft Portable 2.7\nby NotTarts\n\nStarted at {}\nData directory: {}\n\n'.format(datetime.now(), os.path.realpath(dataDir)))

checkForExternal() # Check for external dropped app
    
user = mcpUserData(config, userFile, key) # Load our user data from wherever, if it exists
launcher = mcpLauncher(launcherFile, launcherUrl) # Downloading launcher

# Finding the Java binaries, checking first in the folder specified by the config, then
# the mcp_data directory, then both the 32-bit and 64-bit Program Files directories.
launcher.findJava([config.javaFolder, dataDir, os.path.join(str(os.getenv('ProgramW6432')), 'Java'),
                  os.path.join(str(os.getenv('ProgramFiles(x86)')), 'Java')])

if arguments.server:
    server = mcpServer(serverFile, serverUrl) # Downloading server
    server.launch(config, launcher) # Launch Minecraft server!
else: launcher.launch(user, config) # Launch Minecraft!

log.write('\nProcess finished.')




