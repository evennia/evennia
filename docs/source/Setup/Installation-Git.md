# Installing with GIT

This installs and runs Evennia from its sources. This is required if you want to contribute to Evennia 
itself or have an easier time exploring the code. See the basic [Installation](./Installation.md) for 
a quick installation of the library. See the [troubleshooting](./Installation-Troubleshooting.md) if you run 
into trouble.

```{important}
If you are converting an existing game from a previous version, [see here](./Installation-Upgrade.md).
```

## Summary

For the impatient. If you have trouble with a step, you should jump on to the
more detailed instructions for your platform.

1. Install Python, GIT and python-virtualenv. Start a Console/Terminal.
2. `cd` to some place you want to do your development (like a folder
   `/home/anna/muddev/` on Linux or a folder in your personal user directory on Windows).
3. `git clone https://github.com/evennia/evennia.git`  (a new folder `evennia` is created)
4. `python3.10 -m venv evenv`  (a new folder `evenv` is created)
5. `source evenv/bin/activate` (Linux, Mac), `evenv\Scripts\activate` (Windows)
6. `pip install -e evennia`
7. `evennia --init mygame`
8. `cd mygame`
9. `evennia migrate`
10. `evennia start` (make sure to make a  superuser when asked)
 
Evennia should now be running and you can connect to it by pointing a web browser to
`http://localhost:4001` or a MUD telnet client to `localhost:4000` (use `127.0.0.1` if your OS does
not recognize `localhost`).

## Linux Install

For Debian-derived systems (like Ubuntu, Mint etc), start a terminal and
install the requirements:

```
sudo apt-get update
sudo apt-get install python3.10 python3.10-venv python3.10-dev gcc
```
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
virtualenv](../Glossary.md#virtualenv).

```
python3.10 -m venv evenv
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

Test that you can run the `evennia` command everywhere while your virtualenv (evenv) is active.

Next you can continue initializing your game from the regular [Installation instructions](./Installation.md).


## Mac Install

The Evennia server is a terminal program. Open the terminal e.g. from
*Applications->Utilities->Terminal*. [Here is an introduction to the Mac
terminal](https://blog.teamtreehouse.com/introduction-to-the-mac-os-x-command-line)
if you are unsure how it works. 

* Python should already be installed but you must make sure it's a high enough version - go for 
 3.10.
([This](https://docs.python-guide.org/en/latest/starting/install/osx/) discusses
 how you may upgrade it). 
* GIT can be obtained with
[git-osx-installer](https://code.google.com/p/git-osx-installer/) or via MacPorts [as described
here](https://git-scm.com/book/en/Getting-Started-Installing-Git#Installing-on-Mac).
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
virtualenv is and why it's useful, see the [Glossary entry on virtualenv](../Glossary.md#virtualenv).

```
python3.10 -m venv evenv 
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

Test that you can run the `evennia` command everywhere while your virtualenv (evenv) is active.

Next you can continue initializing your game from the regular [Installation instructions](./Installation.md).

## Windows Install

> If you are running Windows10, consider using the _Windows Subsystem for Linux_
> ([WSL](https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux)) instead.
> Just set up WSL with an Ubuntu image and follow the Linux install instructions above.

The Evennia server itself is a command line program. In the Windows launch
menu, start *All Programs -> Accessories -> command prompt* and you will get
the Windows command line interface. Here is [one of many tutorials on using the Windows command
line](https://www.bleepingcomputer.com/tutorials/windows-command-prompt-introduction/)
if you are unfamiliar with it.

* Install Python [from the Python homepage](https://www.python.org/downloads/windows/). You will
need to be a
Windows Administrator to install packages. Get Python any version of Python **3.10**, usually
the 64-bit version (although it doesn't matter too much). **When installing, make sure
to check-mark *all* install options, especially the one about making Python
available on the path (you may have to scroll to see it)**. This allows you to
just write `python` in any console without first finding where the `python`
program actually sits on your hard drive.
* You need to also get [GIT](https://git-scm.com/downloads) and install it. You
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
virtualenv is and why it's useful, see the [Glossary entry on virtualenv](../Glossary.md#virtualenv).

```
python3.10 -m venv evenv 
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

Test that you can run the `evennia` command everywhere while your virtualenv (evenv) is active.

Next you can continue initializing your game from the regular [Installation instructions](./Installation.md).