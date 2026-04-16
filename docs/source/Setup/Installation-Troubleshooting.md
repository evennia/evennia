# Installation Troubleshooting

If you have an issue not covered here, [please report it](https://github.com/evennia/evennia/issues/new/choose) so it can be fixed or a workaround found!

The server logs are in `mygame/server/logs/`. To easily view server logs in the terminal,
you can run `evennia -l`, or start/reload the server with `evennia start -l` or `evennia reload -l`.

## Check your Requirements

Any system that supports Python3.10+ should work.
- Linux/Unix
- Windows (Win7, Win8, Win10, Win11)
- Mac OSX (>10.5 recommended)

- [Python](https://www.python.org) (3.11, 3.12  and 3.13 are tested. 3.13 is recommended)
- [Twisted](https://twistedmatrix.com) (v24.11+)
    - [ZopeInterface](https://www.zope.org/Products/ZopeInterface) (v3.0+)  - usually included in Twisted packages
    - Linux/Mac users may need the `gcc` and `python-dev` packages or equivalent.
    - Windows users need [MS Visual C++](https://aka.ms/vs/16/release/vs_buildtools.exe) and *maybe* [pypiwin32](https://pypi.python.org/pypi/pypiwin32).
- [Django](https://www.djangoproject.com) (v5.2+), be warned that latest dev version is usually untested with Evennia.
- [GIT](https://git-scm.com/) - version control software used if you want to install the sources (but also useful to track your own code)
  -  Mac users can use the  [git-osx-installer](https://code.google.com/p/git-osx-installer/) or the  [MacPorts version](https://git-scm.com/book/en/Getting-Started-Installing-Git#Installing-on-Mac).

## Confusion of location (GIT installation)

When doing the [Git installation](./Installation-Git.md), some may be confused and install Evennia in the wrong location. After following the instructions (and using a virtualenv), the folder structure should look like this:

```
muddev/
    evenv/
    evennia/
    mygame/
```

The evennia library code itself is found inside `evennia/evennia/` (so two levels down). You shouldn't change this; do all work in `mygame/`.  Your settings file  is `mygame/server/conf/settings.py` and the _parent_ setting file is `evennia/evennia/settings_default.py`.

## Virtualenv setup fails

When doing the `python3.x -m venv evenv` (where x is the python3 version) step, some users report getting an error; something like:

    Error: Command '['evenv', '-Im', 'ensurepip', '--upgrade', '--default-pip']'
    returned non-zero exit status 1

You can solve this by installing the `python3.11-venv` (or later) package (or equivalent for your OS). Alternatively you can bootstrap it in this way:

    python3.x -m --without-pip evenv

This should set up the virtualenv without `pip`. Activate the new virtualenv and then install pip from within it (you don't need to specify the python version once virtualenv is active):

    python -m ensurepip --upgrade

If that fails, a worse alternative to try is

    curl https://bootstrap.pypa.io/get-pip.py | python3.x    (linux/unix/WSL only)

Either way, you should now be able to continue with the installation.

## Localhost not found

If `localhost` doesn't work when trying to connect to your local game, try `127.0.0.1`, which is the same thing.

## Linux Troubleshooting

- If you get an error when installing Evennia (especially with lines mentioning
  failing to include `Python.h`) then try `sudo apt-get install python3-setuptools python3-dev`.  Once installed, run `pip install -e evennia` again.
- When doing a [git install](./Installation-Git.md), some not-updated Linux distributions may give errors
  about a too-old `setuptools` or missing `functools`. If so, update your environment
  with `pip install --upgrade pip wheel setuptools`. Then try `pip install -e evennia` again.
- One user reported a rare issue on Ubuntu 16 is an install error on installing Twisted; `Command "python setup.py egg_info" failed with error code 1 in /tmp/pip-build-vnIFTg/twisted/` with errors  like `distutils.errors.DistutilsError: Could not find suitable distribution for Requirement.parse('incremental>=16.10.1')`. This appears possible to solve by simply updating Ubuntu with `sudo apt-get update && sudo apt-get dist-upgrade`.
- Users of Fedora (notably Fedora 24) has reported a `gcc` error saying the directory
  `/usr/lib/rpm/redhat/redhat-hardened-cc1` is missing, despite `gcc` itself being installed. [The
  confirmed work-around](https://gist.github.com/yograterol/99c8e123afecc828cb8c) seems to be to  install the `redhat-rpm-config` package with e.g. `sudo dnf install redhat-rpm-config`.
- Some users trying to set up a virtualenv on an NTFS filesystem find that it fails due to issues with symlinks not being supported. Answer is to not use NTFS (seriously, why would you do that to  yourself?)

## Mac Troubleshooting

- Some Mac users have reported not being able to connect to `localhost` (i.e. your own computer). If  so, try to connect to `127.0.0.1` instead, which is the same thing. Use port 4000 from mud clients  and port 4001 from the web browser as usual.
- If you get a `MemoryError` when starting Evennia, or when looking at the log, this may be due to an sqlite versioning issue. [A user in our forums](https://github.com/evennia/evennia/discussions/2637) found a working solution for this. [Here](https://github.com/evennia/evennia/issues/2854) is another variation to solve it. [Another user](https://github.com/evennia/evennia/issues/3704) also wrote an extensive summary of the issue, along with troubleshooting instructions.

## Windows Troubleshooting

- If you install with `pip install evennia` and find that the `evennia` command is not available, run `py -m evennia` once. This should add the evennia binary to your environment. If this fails, make sure you are using a [virtualenv](./Installation-Git.md#virtualenv). Worst case, you can keep using `py -m evennia` in the places where the `evennia` command is used.
- - If you get a `command not found` when trying to run the `evennia` program directly after installation, try closing the Windows Console and starting it again (remember to re-activate the virtualenv if you use one!). Sometimes Windows is not updating its environment properly and `evennia` will be available only in the new console.
- If you installed Python but the `python` command is not available (even in a new console), then you might have missed installing Python on the path. In the Windows Python installer you get a list  of options for what to install. Most or all options are pre-checked except this one, and you may  even have to scroll down to see it. Reinstall Python and make sure it's checked. Install Python [from the Python homepage](https://www.python.org/downloads/windows/). You will  need to be a Windows Administrator to install packages.
- If your MUD client cannot connect to `localhost:4000`, try the equivalent `127.0.0.1:4000`  instead. Some MUD clients on Windows does not appear to understand the alias `localhost`.
- Some Windows users get an error installing the Twisted 'wheel'. A wheel is a pre-compiled binary package for Python. A common reason for this error is that you are using a 32-bit version of Python,  but Twisted has not yet uploaded the latest 32-bit wheel. Easiest way to fix this is to install a  slightly older Twisted version. So if, say, version `22.1` failed, install `22.0` manually with `pip install twisted==22.0`. Alternatively you could check that you are using the 64-bit version of Python  and uninstall any 32bit one. If so, you must then `deactivate` the virtualenv, delete the `evenv` folder   and recreate it anew with your new Python.
- If you've done a git installation, and your server won't start with an error message like `AttributeError: module 'evennia' has no attribute '_init'`, it may be a python path issue. In a terminal, cd to `(your python directory)\site-packages` and run the command `echo "C:\absolute\path\to\evennia" > local-vendors.pth`. Open the created file in your favorite IDE and make sure it is saved with *UTF-8* encoding and not *UTF-8 with BOM*.
- Some users have reported issues with Windows WSL and anti-virus software during Evennia development. Timeout errors and the inability to run `evennia connections` may be due to your anti-virus software interfering. Try disabling or changing your anti-virus software settings.
