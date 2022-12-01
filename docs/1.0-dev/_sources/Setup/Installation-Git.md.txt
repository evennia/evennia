# Installing with GIT

This installs and runs Evennia from its sources. This is required if you want to contribute to Evennia itself or have an easier time exploring the code. See the basic [Installation](./Installation.md) for
a quick installation of the library. See the [troubleshooting](./Installation-Troubleshooting.md) if you run
into trouble.

```{important}
If you are converting an existing game from a previous version, [see here](./Installation-Upgrade.md).
```

## Summary

For the impatient. If you have trouble with a step, you should jump on to the
more detailed instructions for your platform.

```{warning}
Currently, these instructions will install 'latest' (stable) Evennia, which is
the 0.9.5 version. To install 1.0-dev, you need to add a step `git checkout develop` between steps
3 and 4 below.
```

1. Install Python and GIT. Start a Console/Terminal.
2. `cd` to some place you want to do your development (like a folder
   `/home/anna/muddev/` on Linux or a folder in your personal user directory on Windows).
3. `git clone https://github.com/evennia/evennia.git`  (a new folder `evennia` is created)
4. `python3.11 -m venv evenv`  (a new folder `evenv` is created)
5. `source evenv/bin/activate` (Linux, Mac), `evenv\Scripts\activate` (Windows)
6. `pip install -e evennia`
7. `evennia --init mygame`
8. `cd mygame`
9. `evennia migrate`
10. `evennia start` (make sure to make a  superuser when asked)

Evennia should now be running and you can connect to it by pointing a web browser to
`http://localhost:4001` or a MUD telnet client to `localhost:4000` (use `127.0.0.1` if your OS does
not recognize `localhost`).

## Virtualenv 

A Python [virtual environment](https://docs.python.org/3/library/venv.html) allows you to install Evennia and all its dependenceis in its own little isolated folder, separate from the rest of the system. This also means you can install without any extra permissions - it all goes into a folder on your drive. 

It's optional to use a virtualenv, but it's highly recommended. Not only is this common Python praxis, it will make your life easier and avoid clashes with other Python programs you may have. 

Python supports virtualenv natively: 

```{sidebar} Using py on Windows
If you have older versions of Python installed on Windows, you should instead use `py` here instead of `python`. The `py` launcher automatically selects the latest python version among those you installed.
```
```bash
python3.11 -m venv evenv   (linux/mac)
python -m venv evenv       (Windows)
```

This will create a new folder `evenv` in your current directory. 
Activate it like this: 

```
source evenv/bin/activate (Linux, Mac)

evenv\Scripts\activate    (Windows Console)

.\evenv\scripts\activate  (Windows PS Shell, 
                           Git Bash etc)
```
The text `(evenv)` should appear next to your prompt to show that the virtual
environment is enabled. You do _not_ need to actually be in or near the `evenv` folder for 
the environment to be active.

```{important}
Remember that you need to (re-)activate the virtualenv like this *every time* you
start a new terminal/console (or restart your computer). Until you do, the `evennia` command will not be available.
```

## Linux Install

For Debian-derived systems (like Ubuntu, Mint etc), start a terminal and
install the requirements:

```bash
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3.11-dev gcc
```
You should make sure to *not* be `root` after this step, running as `root` is a
security risk. Now create a folder where you want to do all your Evennia
development:

```bash
mkdir muddev
cd muddev
```

Next we fetch Evennia itself:

```
git clone https://github.com/evennia/evennia.git
```
A new folder `evennia` will appear containing the Evennia library. This only
contains the source code though, it is not *installed* yet. 

At this point it's now optional but recommended that you initialize and activate a [virtualenv](#virtualenv). 

Next, install Evennia (system-wide, or into your active virtualenv). Make sure you are standing
at the top of your mud directory tree (so you see the `evennia/` folder, and likely the `evenv` virtualenv folder) and do
```{sidebar} 
The `-e ` means that we install evennia in editable mode. If you want to develop on Evennia itself, it means that changes you do to the code is immediately reflected on your running server (you don't have to reinstall every time you make a change).
```
```
pip install -e evennia
```

Test that you can run the `evennia` command.

Next you can continue initializing your game from the regular [Installation instructions](./Installation.md).


## Mac Install

The Evennia server is a terminal program. Open the terminal e.g. from
*Applications->Utilities->Terminal*. [Here is an introduction to the Mac terminal](https://blog.teamtreehouse.com/introduction-to-the-mac-os-x-command-line) if you are unsure how it works.

* Python should already be installed but you must make sure it's a high enough version - go for 3.11. ([This](https://docs.python-guide.org/en/latest/starting/install/osx/) discusses how you may upgrade it).
* GIT can be obtained with [git-osx-installer](https://code.google.com/p/git-osx-installer/) or via MacPorts [as described here](https://git-scm.com/book/en/Getting-Started-Installing-Git#Installing-on-Mac).
* If you run into issues with installing `Twisted` later you may need to install `gcc` and the Python headers.

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

A new folder `evennia` will appear containing the Evennia library. This only contains the source code though, it is not *installed* yet. 

At this point it's now optional but recommended that you initialize and activate a [virtualenv](#virtualenv). 

Next, install Evennia (system-wide, or into your active virtualenv). Make sure you are standing
at the top of your mud directory tree (so you see the `evennia/`, and likely the `evenv` virtualenv 
folder) and do

```
pip install --upgrade pip   # Old pip versions may be an issue on Mac.
pip install --upgrade setuptools   # Ditto concerning Mac issues.
pip install -e evennia
```

Test that you can run the `evennia` command. 

Next you can continue initializing your game from the regular [Installation instructions](./Installation.md).

## Windows Install

> If you are running Windows10+, consider using the _Windows Subsystem for Linux_ > ([WSL](https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux)) instead. Just set up WSL with an Ubuntu image and follow the Linux install instructions above.

The Evennia server itself is a command line program. In the Windows launch menu, start *All Programs -> Accessories -> command prompt* and you will get the Windows command line interface. Here is [one of many tutorials on using the Windows command line](https://www.bleepingcomputer.com/tutorials/windows-command-prompt-introduction/) if you are unfamiliar with it.

* Install Python [from the Python homepage](https://www.python.org/downloads/windows/). You will need to be a Windows Administrator to install packages. Get Python **3.11**, 64-bit version. Use the default settings; make sure the `py` launcher gets installed. 
* You need to also get [GIT](https://git-scm.com/downloads) and install it. You can use the default install options but when you get asked to "Adjust your PATH environment", you should select the second option "Use Git from the Windows Command Prompt", which gives you more freedom as to where you can use the program.
* If you run Python 3.11: You must also install the [Windows SDK](https://aka.ms/vs/16/release/vs_buildtools.exe). Download and run the linked installer. Click the  `Individual Components` tab at the top. Search and checkmark the latest `Windows 10 SDK` (also for older and newer Windows versions). Click `Install`. If you later have issues with installing Evennia due to a failure to build the "Twisted wheels", this is where you are missing things. If you have trouble, use Python 3.10 for now (2022)
* You *may* need the [pypiwin32](https://pypi.python.org/pypi/pypiwin32) Python headers. Install these only if you have issues.

You can install Evennia wherever you want. `cd` to that location and create a
new folder for all your Evennia development (let's call it `muddev`).

```
mkdir muddev
cd muddev
```

> If `cd` isn't working you can use `pushd` instead to force the directory change.

Next we fetch Evennia itself:

```
git clone https://github.com/evennia/evennia.git
```

A new folder `evennia` will appear containing the Evennia library. This only
contains the source code though, it is not *installed* yet. 

At this point it's optional but recommended that you initialize and activate a [virtualenv](#virtualenv). 

Next, install Evennia (system wide, or into the virtualenv). Make sure you are standing
at the top of your mud directory tree (so you see `evennia`, and likely the `evenv`  virtualenv folder when running the `dir` command). Then do: 

```
pip install -e evennia
```

Test that you can run the `evennia` command everywhere while your virtualenv (evenv) is active.

Next you can continue initializing your game from the regular [Installation instructions](./Installation.md).
