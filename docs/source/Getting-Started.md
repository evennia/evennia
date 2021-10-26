# Getting Started


This will help you download, install and start Evennia for the first time.

> Note: You don't need to make anything visible to the 'net in order to run and
> test out Evennia. Apart from downloading and updating you don't even need an
> internet connection until you feel ready to share your game with the world.

- [Quick Start](./Getting-Started.md#quick-start)
- [Requirements](./Getting-Started.md#requirements)
- [Linux Install](./Getting-Started.md#linux-install)
- [Mac Install](./Getting-Started.md#mac-install)
- [Windows Install](./Getting-Started.md#windows-install)
- [Running in Docker](./Running-Evennia-in-Docker.md)
- [Where to Go Next](./Getting-Started.md#where-to-go-next)
- [Troubleshooting](./Getting-Started.md#troubleshooting)
- [Glossary of terms](./Glossary.md)

## Quick Start

For the impatient. If you have trouble with a step, you should jump on to the
more detailed instructions for your platform.

1. Install Python, GIT and python-virtualenv. Start a Console/Terminal.
2. `cd` to some place you want to do your development (like a folder
   `/home/anna/muddev/` on Linux or a folder in your personal user directory on Windows).
3. `git clone https://github.com/evennia/evennia.git`
4. `virtualenv evenv`
5. `source evenv/bin/activate` (Linux, Mac), `evenv\Scripts\activate` (Windows)
6. `pip install -e evennia`
7. `evennia --init mygame`
8. `cd mygame`
9. `evennia migrate`
10. `evennia start` (make sure to make a  superuser when asked)
Evennia should now be running and you can connect to it by pointing a web browser to
`http://localhost:4001` or a MUD telnet client to `localhost:4000` (use `127.0.0.1` if your OS does
not recognize `localhost`).

We also release [Docker images](./Running-Evennia-in-Docker.md)
based on `master` and `develop` branches.

## Requirements

Any system that supports Python3.7+ should work. We'll describe how to install
everything in the following sections.
- Linux/Unix
- Windows (Vista, Win7, Win8, Win10)
- Mac OSX (>=10.5 recommended)

- [Python](http://www.python.org) (v3.7, 3.8 or 3.9)
  - [virtualenv](http://pypi.python.org/pypi/virtualenv) for making isolated
    Python environments. Installed with `pip install virtualenv`.

- [GIT](http://git-scm.com/) - version control software for getting and
updating Evennia itself - Mac users can use the
[git-osx-installer](http://code.google.com/p/git-osx-installer/) or the
[MacPorts version](http://git-scm.com/book/en/Getting-Started-Installing-Git#Installing-on-Mac).
- [Twisted](http://twistedmatrix.com) (v21.0+)
  - [ZopeInterface](http://www.zope.org/Products/ZopeInterface) (v3.0+)  - usually included in
Twisted packages
  - Linux/Mac users may need the `gcc` and `python-dev` packages or equivalent.
  - Windows users need [MS Visual C++](https://aka.ms/vs/16/release/vs_buildtools.exe) and *maybe*
[pypiwin32](https://pypi.python.org/pypi/pypiwin32).
- [Django](http://www.djangoproject.com) (v3.2.x), be warned that latest dev
  version is usually untested with Evennia)

## Linux Install

If you run into any issues during the installation and first start, please
check out [Linux Troubleshooting](./Getting-Started.md#linux-troubleshooting).

For Debian-derived systems (like Ubuntu, Mint etc), start a terminal and
install the [dependencies](./Getting-Started.md#requirements):

```
sudo apt-get update
sudo apt-get install python3 python3-pip python3-dev python3-setuptools python3-git
python3-virtualenv gcc

# If you are using an Ubuntu version that defaults to Python3, like 18.04+, use this instead:
sudo apt-get update
sudo apt-get install python3.7 python3-pip python3.7-dev python3-setuptools virtualenv gcc

```
Note that, the default Python version for your distribution may still not be Python3.7 after this.
This is ok - we'll specify exactly which Python to use later.
You should make sure to *not* be `root` after this step, running as `root` is a
security risk. Now create a folder where you want to do all your Evennia
development:

```
mkdir muddev
cd muddev
```

Next we fetch Evennia itself:

```
git clone https://github.com/evennia/evennia.git
```
A new folder `evennia` will appear containing the Evennia library. This only
contains the source code though, it is not *installed* yet. To isolate the
Evennia install and its dependencies from the rest of the system, it is good
Python practice to install into a _virtualenv_. If you are unsure about what a
virtualenv is and why it's useful, see the [Glossary entry on
virtualenv](./Glossary.md#virtualenv).

Run `python -V` to see which version of Python your system defaults to.

```
# If your Linux defaults to Python3.7+:
virtualenv evenv

# If your Linux defaults to Python2 or an older version
# of Python3, you must instead point to Python3.7+ explicitly:
virtualenv -p /usr/bin/python3.7 evenv
```

A new folder `evenv` will appear (we could have called it anything). This
folder will hold a self-contained setup of Python packages without interfering
with default Python packages on your system (or the Linux distro lagging behind
on Python package versions). It will also always use the right version of Python.
Activate the virtualenv:

```
source evenv/bin/activate
```

The text `(evenv)` should appear next to your prompt to show that the virtual
environment is active.

> Remember that you need to activate the virtualenv like this *every time* you
> start a new terminal to get access to the Python packages (notably the
> important `evennia` program) we are about to install.

Next, install Evennia into your active virtualenv. Make sure you are standing
at the top of your mud directory tree (so you see the `evennia/` and `evenv/`
folders) and run

```
pip install -e evennia
```

For more info about `pip`, see the [Glossary entry on pip](./Glossary.md#pip). If
install failed with any issues, see [Linux Troubleshooting](./Getting-Started.md#linux-troubleshooting).

Next we'll start our new game, here called "mygame". This will create yet
another new folder where you will be creating your new game:

```
evennia --init mygame
```

Your final folder structure should look like this:
```
./muddev
    evenv/
    evennia/
    mygame/
```

You can [configure Evennia](./Server-Conf.md#settings-file) extensively, for example
to use a [different database](./Choosing-An-SQL-Server.md). For now we'll just stick
to the defaults though.

```
cd mygame
evennia migrate      # (this creates the database)
evennia start        # (create a superuser when asked. Email is optional.)
```

> Server logs are found in `mygame/server/logs/`. To easily view server logs
> live in the terminal, use `evennia -l` (exit the log-view with Ctrl-C).

Your game should now be running! Open a web browser at `http://localhost:4001`
or point a telnet client to `localhost:4000` and log in with the user you
created. Check out [where to go next](./Getting-Started.md#where-to-go-next).


## Mac Install

The Evennia server is a terminal program. Open the terminal e.g. from
*Applications->Utilities->Terminal*. [Here is an introduction to the Mac
terminal](http://blog.teamtreehouse.com/introduction-to-the-mac-os-x-command-line)
if you are unsure how it works. If you run into any issues during the
installation, please check out [Mac Troubleshooting](./Getting-Started.md#mac-troubleshooting).

* Python should already be installed but you must make sure it's a high enough version.
([This](http://docs.python-guide.org/en/latest/starting/install/osx/) discusses
 how you may upgrade it). Remember that you need Python3.7, not Python2.7!
* GIT can be obtained with
[git-osx-installer](http://code.google.com/p/git-osx-installer/) or via
MacPorts [as described
here](http://git-scm.com/book/en/Getting-Started-Installing-Git#Installing-on-Mac).
* If you run into issues with installing `Twisted` later you may need to
install gcc and the Python headers.

After this point you should not need `sudo` or any higher privileges to install anything.

Now create a folder where you want to do all your Evennia development:

```
mkdir muddev
cd muddev
```

Next we fetch Evennia itself:

```
git clone https://github.com/evennia/evennia.git
```

A new folder `evennia` will appear containing the Evennia library. This only
contains the source code though, it is not *installed* yet. To isolate the
Evennia install and its dependencies from the rest of the system, it is good
Python practice to install into a _virtualenv_. If you are unsure about what a
virtualenv is and why it's useful, see the [Glossary entry on virtualenv](./Glossary.md#virtualenv).

Run `python -V` to check which Python your system defaults to.


```
# If your Mac defaults to Python3:
virtualenv evenv

# If your Mac defaults to Python2 you need to specify the Python3.7 binary explicitly:
virtualenv -p /path/to/your/python3.7 evenv
```

A new folder `evenv` will appear (we could have called it anything). This
folder will hold a self-contained setup of Python packages without interfering
with default Python packages on your system. Activate the virtualenv:

```
source evenv/bin/activate
```

The text `(evenv)` should appear next to your prompt to show the virtual
environment is active.

> Remember that you need to activate the virtualenv like this *every time* you
> start a new terminal to get access to the Python packages (notably the
> important `evennia` program) we are about to install.

Next, install Evennia into your active virtualenv. Make sure you are standing
at the top of your mud directory tree (so you see the `evennia/` and `evenv/`
folders) and run

```
pip install --upgrade pip   # Old pip versions may be an issue on Mac.
pip install --upgrade setuptools   # Ditto concerning Mac issues.
pip install -e evennia
```

For more info about `pip`, see the [Glossary entry on pip](./Glossary.md#pip). If
install failed with any issues, see [Mac Troubleshooting](./Getting-Started.md#mac-troubleshooting).

Next we'll start our new game. We'll call it "mygame" here. This creates a new
folder where you will be creating your new game:

```
evennia --init mygame
```

Your final folder structure should look like this:

```
./muddev
    evenv/
    evennia/
    mygame/
```

You can [configure Evennia](./Server-Conf.md#settings-file) extensively, for example
to use a [different database](./Choosing-An-SQL-Server.md). We'll go with the
defaults here.

```
cd mygame
evennia migrate  # (this creates the database)
evennia start    # (create a superuser when asked. Email is optional.)
```

> Server logs are found in `mygame/server/logs/`. To easily view server logs
> live in the terminal, use `evennia -l` (exit the log-view with Ctrl-C).

Your game should now be running! Open a web browser at `http://localhost:4001`
or point a telnet client to `localhost:4000` and log in with the user you
created. Check out [where to go next](./Getting-Started.md#where-to-go-next).


## Windows Install

If you run into any issues during the installation, please check out
[Windows Troubleshooting](./Getting-Started.md#windows-troubleshooting).

> If you are running Windows10, consider using the Windows Subsystem for Linux
> ([WSL](https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux)) instead.
> You should then follow the Linux install instructions above.

The Evennia server itself is a command line program. In the Windows launch
menu, start *All Programs -> Accessories -> command prompt* and you will get
the Windows command line interface. Here is [one of many tutorials on using the Windows command
line](http://www.bleepingcomputer.com/tutorials/windows-command-prompt-introduction/)
if you are unfamiliar with it.

* Install Python [from the Python homepage](https://www.python.org/downloads/windows/). You will
need to be a
Windows Administrator to install packages. You want Python version **3.7.0** (latest verified
version), usually
the 64-bit version (although it doesn't matter too much). **When installing, make sure
to check-mark *all* install options, especially the one about making Python
available on the path (you may have to scroll to see it)**. This allows you to
just write `python` in any console without first finding where the `python`
program actually sits on your hard drive.
* You need to also get [GIT](http://git-scm.com/downloads) and install it. You
can use the default install options but when you get asked to "Adjust your PATH
environment", you should select the second option "Use Git from the Windows
Command Prompt", which gives you more freedom as to where you can use the
program.
* Finally you must install the [Microsoft Visual C++ compiler for
Python](https://aka.ms/vs/16/release/vs_buildtools.exe). Download and run the linked installer and
install the C++ tools. Keep all the defaults. Allow the install of the "Win10 SDK", even if you are
on Win7 (not tested on older Windows versions). If you later have issues with installing Evennia due
to a failure to build the "Twisted wheels", this is where you are missing things.
* You *may* need the [pypiwin32](https://pypi.python.org/pypi/pypiwin32) Python headers. Install
these only if you have issues.

You can install Evennia wherever you want. `cd` to that location and create a
new folder for all your Evennia development (let's call it `muddev`).

```
mkdir muddev
cd muddev
```

> Hint: If `cd` isn't working you can use `pushd` instead to force the
> directory change.

Next we fetch Evennia itself:

```
git clone https://github.com/evennia/evennia.git
```

A new folder `evennia` will appear containing the Evennia library. This only
contains the source code though, it is not *installed* yet. To isolate the
Evennia install and its dependencies from the rest of the system, it is good
Python practice to install into a _virtualenv_. If you are unsure about what a
virtualenv is and why it's useful, see the [Glossary entry on virtualenv](./Glossary.md#virtualenv).

In your console, try `python -V` to see which version of Python your system
defaults to.


```
pip install virtualenv

# If your setup defaults to Python3.7:
virtualenv evenv

# If your setup defaults to Python2, specify path to python3.exe explicitly:
virtualenv -p C:\Python37\python.exe evenv

# If you get an infinite spooling response, press CTRL + C to interrupt and try using:
python -m venv evenv

```
A new folder `evenv` will appear (we could have called it anything). This
folder will hold a self-contained setup of Python packages without interfering
with default Python packages on your system. Activate the virtualenv:

```
# If you are using a standard command prompt, you can use the following:
evenv\scripts\activate.bat

# If you are using a PS Shell, Git Bash, or other, you can use the following:
.\evenv\scripts\activate

```
The text `(evenv)` should appear next to your prompt to show the virtual
environment is active.

> Remember that you need to activate the virtualenv like this *every time* you
> start a new console window if you want to get access to the Python packages
> (notably the important `evennia` program) we are about to install.

Next, install Evennia into your active virtualenv. Make sure you are standing
at the top of your mud directory tree (so you see the `evennia` and `evenv`
folders when you use the `dir` command) and run

```
pip install -e evennia
```
For more info about `pip`, see the [Glossary entry on pip](./Glossary.md#pip). If
the install failed with any issues, see [Windows Troubleshooting](./Getting-Started.md#windows-
troubleshooting).
Next we'll start our new game, we'll call it "mygame" here. This creates a new folder where you will
be
creating your new game:

```
evennia --init mygame
```

Your final folder structure should look like this:

```
path\to\muddev
    evenv\
    evennia\
    mygame\
```

You can [configure Evennia](./Server-Conf.md#settings-file) extensively, for example
to use a [different database](./Choosing-An-SQL-Server.md). We'll go with the
defaults here.

```
cd mygame
evennia migrate    # (this creates the database)
evennia start      # (create a superuser when asked. Email is optional.)
```

> Server logs are found in `mygame/server/logs/`. To easily view server logs
> live in the terminal, use `evennia -l` (exit the log-view with Ctrl-C).

Your game should now be running! Open a web browser at `http://localhost:4001`
or point a telnet client to `localhost:4000` and log in with the user you
created. Check out [where to go next](./Getting-Started.md#where-to-go-next).


## Where to Go Next

Welcome to Evennia! Your new game is fully functioning, but empty. If you just
logged in, stand in the `Limbo` room and run

    @batchcommand tutorial_world.build

to build [Evennia's tutorial world](./Tutorial-World-Introduction.md) - it's a small solo quest to
explore. Only run the instructed `@batchcommand` once. You'll get a lot of text scrolling by as the
tutorial is built. Once done, the `tutorial` exit will have appeared out of Limbo - just write
`tutorial` to enter it.

Once you get back to `Limbo` from the tutorial (if you get stuck in the tutorial quest you can do
`@tel #2` to jump to Limbo), a good idea is to learn how to [start, stop and reload](Start-Stop-
Reload) the Evennia server. You may also want to familiarize yourself with some [commonly used terms
in our Glossary](./Glossary.md). After that, why not experiment with [creating some new items and build
some new rooms](./Building-Quickstart.md) out from Limbo.

From here on, you could move on to do one of our [introductory tutorials](./Tutorials.md) or simply dive
headlong into Evennia's comprehensive [manual](https://github.com/evennia/evennia/wiki). While
Evennia has no major game systems out of the box, we do supply a range of optional *contribs* that
you can use or borrow from. They range from dice rolling and alternative color schemes to barter and
combat systems. You can find the [growing list of contribs
here](https://github.com/evennia/evennia/blob/master/evennia/contrib/README.md).

If you have any questions, you can always ask in [the developer
chat](http://webchat.freenode.net/?channels=evennia&uio=MT1mYWxzZSY5PXRydWUmMTE9MTk1JjEyPXRydWUbb)
`#evennia` on `irc.freenode.net` or by posting to the [Evennia
forums](https://groups.google.com/forum/#%21forum/evennia). You can also join the [Discord
Server](https://discord.gg/NecFePw).

Finally, if you are itching to help out or support Evennia (awesome!) have an
issue to report or a feature to request, [see here](./How-To-Get-And-Give-Help.md).

Enjoy your stay!


## Troubleshooting

If you have issues with installing or starting Evennia for the first time,
check the section for your operating system below. If you have an issue not
covered here, [please report it](https://github.com/evennia/evennia/issues)
so it can be fixed or a workaround found!

Remember, the server logs are in `mygame/server/logs/`. To easily view server logs in the terminal,
you can run `evennia -l`, or (in the future) start the server with `evennia start -l`.

### Linux Troubleshooting

- If you get an error when installing Evennia (especially with lines mentioning
  failing to include `Python.h`) then try `sudo apt-get install python3-setuptools python3-dev`.
  Once installed, run `pip install -e evennia` again.
- Under some not-updated Linux distributions you may run into errors with a
  too-old `setuptools` or missing `functools`. If so, update your environment
  with `pip install --upgrade pip wheel setuptools`. Then try `pip install -e evennia` again.
- If you get an `setup.py not found` error message while trying to `pip install`, make sure you are
  in the right directory. You should be at the same level of the `evenv` directory, and the
  `evennia` git repository. Note that there is an `evennia` directory inside of the repository too.
- One user reported a rare issue on Ubuntu 16 is an install error on installing Twisted; `Command
"python setup.py egg_info" failed with error code 1 in /tmp/pip-build-vnIFTg/twisted/` with errors
like `distutils.errors.DistutilsError: Could not find suitable distribution for
Requirement.parse('incremental>=16.10.1')`. This appears possible to solve by simply updating Ubuntu
with `sudo apt-get update && sudo apt-get dist-upgrade`.
- Users of Fedora (notably Fedora 24) has reported a `gcc` error saying the directory
`/usr/lib/rpm/redhat/redhat-hardened-cc1` is missing, despite `gcc` itself being installed. [The
confirmed work-around](https://gist.github.com/yograterol/99c8e123afecc828cb8c) seems to be to
install the `redhat-rpm-config` package with e.g. `sudo dnf install redhat-rpm-config`.
- Some users trying to set up a virtualenv on an NTFS filesystem find that it fails due to issues
with symlinks not being supported. Answer is to not use NTFS (seriously, why would you do that to
yourself?)

### Mac Troubleshooting

- Mac users have reported a critical `MemoryError` when trying to start Evennia on Mac with a Python
version below `2.7.12`. If you get this error, update to the latest XCode and Python2 version.
- Some Mac users have reported not being able to connect to `localhost` (i.e. your own computer). If
so, try to connect to `127.0.0.1` instead, which is the same thing. Use port 4000 from mud clients
and port 4001 from the web browser as usual.

### Windows Troubleshooting

- If you installed Python but the `python` command is not available (even in a new console), then
you might have missed installing Python on the path. In the Windows Python installer you get a list
of options for what to install. Most or all options are pre-checked except this one, and you may
even have to scroll down to see it. Reinstall Python and make sure it's checked.
- If your MUD client cannot connect to `localhost:4000`, try the equivalent `127.0.0.1:4000`
instead. Some MUD clients on Windows does not appear to understand the alias `localhost`.
- If you run `virtualenv evenv` and get a `'virtualenv' is not recognized as an internal or external
command,
operable program or batch file.` error, you can `mkdir evenv`, `cd evenv` and then `python -m
virtualenv .` as a workaround.
- Some Windows users get an error installing the Twisted 'wheel'. A wheel is a pre-compiled binary
package for Python. A common reason for this error is that you are using a 32-bit version of Python,
but Twisted has not yet uploaded the latest 32-bit wheel. Easiest way to fix this is to install a
slightly older Twisted version. So if, say, version `18.1` failed, install `18.0` manually with `pip
install twisted==18.0`. Alternatively you could try to get a 64-bit version of Python (uninstall the
32bit one). If so, you must then `deactivate` the virtualenv, delete the `evenv` folder and recreate
it anew (it will then use the new Python executable).
- If your server won't start, with no error messages (and no log files at all when starting from
scratch), try to start with `evennia ipstart` instead. If you then see an error about `system cannot
find the path specified`, it may be that the file `evennia/evennia/server/twistd.bat` has the wrong
path to the `twistd` executable. This file is auto-generated, so try to delete it and then run
`evennia start` to rebuild it and see if it works. If it still doesn't work you need to open it in a
text editor like Notepad. It's just one line containing  the path to the `twistd.exe` executable as
determined by Evennia. If you installed Twisted in a non-standard location this might be wrong and
you should update the line to the real location.
- Some users have reported issues with Windows WSL and anti-virus software during Evennia
development. Timeout errors and the inability to run `evennia connections` may be due to your anti-
virus software interfering. Try disabling or changing your anti-virus software settings.
