#Hosting Documentation

This documentation covers installation of Evennia in a production environment on either Linux or Windows.

> Note: You don't need to make anything visible to the 'net in order to run and
> test out Evennia. Apart from downloading and updating you don't even need an
> internet connection until you feel ready to share your game with the world.

The vast majority of systems in operation today should support Evennia.


##Installation
**Linux/Unix**

1. Install dependencies: `sudo apt-get install python3 git` 
2. Create a folder you would like Evennia to live in
3. Open a Terminal and navigate to this folder
4. Run the following commands
```linux
git clone https://github.com/evennia/evennia.git
python3 -m virtualenv evenv
source evenv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -e evennia
evennia --init mygame
cd mygame
evennia migrate
evennia start` (make sure to make a  superuser when asked)
 ```

***

**MacOS**

1. Install [Python 3.8](http://www.python.org) and [Git](http://code.google.com/p/git-osx-installer/)
2. Follow the Linux instructions above, starting from Step 2

***

**Windows (Vista, Win7, Win8, Win10)**

1. Install [Python 3.8](http://www.python.org) and [Git](http://git-scm.com/)
2. Create a folder you would like Evennia to live in
3. Open a Command Prompt and navigate to this folder
4. Run the following commands

```windows
git clone https://github.com/evennia/evennia.git
python -m virtualenv evenv
source evenv\Scripts\activate
pip install --upgrade pip wheel setuptools
pip install -e evennia
evennia --init mygame
cd mygame
evennia migrate
evennia start` (make sure to make a  superuser when asked)
 ```

***

**Docker**

We also release [Docker images](DockerDocs) based on `master` and `develop` branches.


## Connecting to Evennia
Evennia should now be running and you can connect to it by pointing a web browser to `http://localhost:4001` 
or a MUD telnet client to `localhost:4000` (use `127.0.0.1` if your OS does not recognize `localhost`).

If you cannot access Evennia by either of the above methods, see the Troubleshooting at the bottom of this page.

**Want to get started building? Head over to the [Builder Documentation](BuilderDocs)!** The rest of this page is geared
primarily towards server-grade hosting for finished games. If you're installing Evennia for the first time, it may be
far over your head, and you probably won't need it!


## Advanced Server Administration
#### Upgrading Evennia
Very commonly we make changes to the Evennia code to improve things. While we try very hard not to introduce changes that will break your game on an upgrade, this is still a beta.  

When you're wanting to apply updates, simply `cd` to your cloned `evennia` root directory and type:

     git pull
     evennia reboot

Note that this will disconnect all connected players.

For more information, particularly when moving between major versions of evennia, read [Updating Your Game](Updating-Your-Game)

_Snekkie says, "There are many ways to get told when to update: You can subscribe to the RSS feed or manually check up on the feeds from http://www.evennia.com. You can also simply fetch the latest regularly."_

#### Logs
The server logs are in `mygame/server/logs/`. To easily view server logs in the terminal,
you can run `evennia -l`, or (in the future) start the server with `evennia start -l`.

#### Game Admin Commands
Evennia supports the following commands. You can use these while inside your `evenv` virtual environment, so
be sure to `source evenv/bin/activate` (Unix) or `source evenv\Scripts\activate` (Windows) before continuing.

- `evennia restart` - The graceful way to restart a server to apply changes. Does not disconnect users.
- `evennia reboot` - Reboots both server and portal, disconnecting all users. Necessary after development changes very "deep" pieces of evennia, like settings.py
- `evennia kill` - The most destructive server restart. Kills processes defined in `server/server.pid` and `server/portal.pid`. Tries to be graceful, but no guarantees.
- `evennia start` - Starts the server
- `evennia stop` - Stops the server gracefully

For more information about these commands, as well as several others that are available, read the detailed guide over at [Stop/Start/Reload](Start-Stop-Reload).

#### Database Management

Database handling is managed by [Django](https://docs.djangoproject.com/en/3.0/ref/databases/). The default database is sqlite3.
To use a different database, edit `server/conf/secret_settings.py` and update the `DATABASES=` key.

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydatabase',
        'USER': 'mydatabaseuser',
        'PASSWORD': 'mypassword',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}
```

The `evennia migrate` command builds the necessary tables. This command should only be run after changes which require the database to be reconstructed from scratch.

#### Protocols/Ports

Your firewall will hopefully block the necessary ports for remote connection on initial installation. The default external ports are described below:

- **4000**: Telnet
- **4001**: HTTP
- **4002**: Websockets

You can change these ports by modifying `settings.py` - defaults are listed below:

**Telnet**
```python
# Activate telnet service
TELNET_ENABLED = True

# A list of ports the Evennia telnet server listens on Can be one or many.
TELNET_PORTS = [4000]

# Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
TELNET_INTERFACES = ["0.0.0.0"]

# OOB (out-of-band) telnet communication allows Evennia to communicate
# special commands and data with enabled Telnet clients. This is used
# to create custom client interfaces over a telnet connection. To make
# full use of OOB, you need to prepare functions to handle the data
# server-side (see INPUT_FUNC_MODULES). TELNET_ENABLED is required for this
# to work.
TELNET_OOB_ENABLED = False
```
**SSL/SSH**
```python
# Activate Telnet+SSL protocol (SecureSocketLibrary) for supporting clients
SSL_ENABLED = False

# Ports to use for Telnet+SSL
SSL_PORTS = [4003]

# Telnet+SSL Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
SSL_INTERFACES = ["0.0.0.0"]

# Activate SSH protocol communication (SecureShell)
SSH_ENABLED = False

# Ports to use for SSH
SSH_PORTS = [4004]

# Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
SSH_INTERFACES = ["0.0.0.0"]
```
**HTTP**
```python
# Start the evennia django+twisted webserver so you can
# browse the evennia website and the admin interface
# (Obs - further web configuration can be found below
# in the section  'Config for Django web features')
WEBSERVER_ENABLED = True

# This is a security setting protecting against host poisoning
# attacks.  It defaults to allowing all. In production, make
# sure to change this to your actual host addresses/IPs.
ALLOWED_HOSTS = ["*"]

# The webserver sits behind a Portal proxy. This is a list
# of tuples (proxyport,serverport) used. The proxyports are what
# the Portal proxy presents to the world. The serverports are
# the internal ports the proxy uses to forward data to the Server-side
# webserver (these should not be publicly open)
WEBSERVER_PORTS = [(4001, 4005)]

# Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
WEBSERVER_INTERFACES = ["0.0.0.0"]

# IP addresses that may talk to the server in a reverse proxy configuration,
# like NginX.
UPSTREAM_IPS = ["127.0.0.1"]

# The webserver uses threadpool for handling requests. This will scale
# with server load. Set the minimum and maximum number of threads it
# may use as (min, max) (must be > 0)
WEBSERVER_THREADPOOL_LIMITS = (1, 20)

# Start the evennia webclient. This requires the webserver to be running and
# offers the fallback ajax-based webclient backbone for browsers not supporting
# the websocket one.
WEBCLIENT_ENABLED = True
```
- [Apache Configuration](Apache-Config)

**Websockets**
```python
# Activate Websocket support for modern browsers. If this is on, the
# default webclient will use this and only use the ajax version if the browser
# is too old to support websockets. Requires WEBCLIENT_ENABLED.
WEBSOCKET_CLIENT_ENABLED = True

# Server-side websocket port to open for the webclient. Note that this value will
# be dynamically encoded in the webclient html page to allow the webclient to call
# home. If the external encoded value needs to be different than this, due to
# working through a proxy or docker port-remapping, the environment variable
# WEBCLIENT_CLIENT_PROXY_PORT can be used to override this port only for the
# front-facing client's sake.
WEBSOCKET_CLIENT_PORT = 4002

# Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
WEBSOCKET_CLIENT_INTERFACE = "0.0.0.0"

# Actual URL for webclient component to reach the websocket. You only need
# to set this if you know you need it, like using some sort of proxy setup.
# If given it must be on the form "ws[s]://hostname[:port]". If left at None,
# the client will itself figure out this url based on the server's hostname.
# e.g. ws://external.example.com or wss://external.example.com:443
WEBSOCKET_CLIENT_URL = None

```
**Lockdown**
```python
# Lockdown mode will cut off the game from any external connections
# and only allow connections from localhost. Requires a cold reboot.
LOCKDOWN_MODE = False
```
**AMP (Internal)**
```
# The Server opens an AMP port so that the portal can
# communicate with it. This is an internal functionality of Evennia, usually
# operating between two processes on the same machine. You usually don't need to
# change this unless you cannot use the default AMP port/host for
# whatever reason.

AMP_HOST = "localhost"
AMP_PORT = 4006
AMP_INTERFACE = "127.0.0.1"
```

##Troubleshooting
#####Python won't start

- `python --version` from a command line should return a supported version of Python. 
If it doesn't, you might try `python3 --version`. If neither of these commands work, 
your system cannot find the python executable. [Read more](https://wiki.python.org/moin/BeginnersGuide/Download)
- Fix: Run the correct Python executable with switches `-m virtualenv evenv`. You may have to explicitly point to your Python executable here, e.g.`C:\Program Files\Python\python.exe -m virtualenv evenv`  
***
#####Missing dependencies

Evennia requires the following dependencies:
- [Python](http://www.python.org) (v3.7, 3.8 are tested)
  - [virtualenv](http://pypi.python.org/pypi/virtualenv) for making isolated
    Python environments. Installed with `pip install virtualenv`.

- [GIT](http://git-scm.com/) - version control software for getting and
updating Evennia itself - Mac users can use the
[git-osx-installer](http://code.google.com/p/git-osx-installer/) or the
[MacPorts version](http://git-scm.com/book/en/Getting-Started-Installing-Git#Installing-on-Mac).
- [Twisted](http://twistedmatrix.com) (v19.0+)
  - [ZopeInterface](http://www.zope.org/Products/ZopeInterface) (v3.0+)  - usually included in Twisted packages
  - Linux/Mac users may need the `gcc` and `python-dev` packages or equivalent.
  - Windows users need [MS Visual C++](https://aka.ms/vs/16/release/vs_buildtools.exe) and *maybe* [pypiwin32](https://pypi.python.org/pypi/pypiwin32).
- [Django](http://www.djangoproject.com) (v2.2.x), be warned that latest dev
  version is usually untested with Evennia)

**Linux/Unix:**
```
sudo apt-get update
sudo apt-get install python3 python3-pip python3-dev python3-setuptools python3-git python3-virtualenv gcc

# If you are using an Ubuntu version that defaults to Python3, like 18.04+, use this instead:
sudo apt-get update
sudo apt-get install python3.7 python3-pip python3.7-dev python3-setuptools virtualenv gcc
``` 

FIX: After installing dependencies, run `pip install -e evennia` again and continue

***

#####Localhost-related issues

Not all computers accept `localhost` as a valid IP address. Swap for `127.0.0.1` - this should always work.
***


#####Other Linux Troubleshooting
- One user reported a rare issue on Ubuntu 16 is an install error on installing Twisted; `Command "python setup.py egg_info" failed with error code 1 in /tmp/pip-build-vnIFTg/twisted/` with errors like `distutils.errors.DistutilsError: Could not find suitable distribution for Requirement.parse('incremental>=16.10.1')`. This appears possible to solve by simply updating Ubuntu with `sudo apt-get update && sudo apt-get dist-upgrade`.
- Users of Fedora (notably Fedora 24) has reported a `gcc` error saying the directory `/usr/lib/rpm/redhat/redhat-hardened-cc1` is missing, despite `gcc` itself being installed. [The confirmed work-around](https://gist.github.com/yograterol/99c8e123afecc828cb8c) seems to be to install the `redhat-rpm-config` package with e.g. `sudo dnf install redhat-rpm-config`.
- Some users trying to set up a virtualenv on an NTFS filesystem find that it fails due to issues with symlinks not being supported. 

***

#####Other Mac Troubleshooting
- No other issues reported. Great job, Steve!

***

#####Other Windows Troubleshooting
- Some Windows users get an error installing the Twisted 'wheel'. A wheel is a pre-compiled binary package for Python. A common reason for this error is that you are using a 32-bit version of Python, but Twisted has not yet uploaded the latest 32-bit wheel. Easiest way to fix this is to install a slightly older Twisted version. So if, say, version `18.1` failed, install `18.0` manually with `pip install twisted==18.0`. Alternatively you could try to get a 64-bit version of Python (uninstall the 32bit one). If so, you must then `deactivate` the virtualenv, delete the `evenv` folder and recreate it anew (it will then use the new Python executable).
- If your server won't start, with no error messages (and no log files at all when starting from scratch), try to start with `evennia ipstart` instead. If you then see an error about `system cannot find the path specified`, it may be that the file `evennia/evennia/server/twistd.bat` has the wrong path to the `twistd` executable. This file is auto-generated, so try to delete it and then run `evennia start` to rebuild it and see if it works. If it still doesn't work you need to open it in a text editor like Notepad. It's just one line containing  the path to the `twistd.exe` executable as determined by Evennia. If you installed Twisted in a non-standard location this might be wrong and you should update the line to the real location. 
