# Installation Troubleshooting

If you have an issue not covered here, [please report it](https://github.com/evennia/evennia/issues/new/choose)
so it can be fixed or a workaround found!

The server logs are in `mygame/server/logs/`. To easily view server logs in the terminal,
you can run `evennia -l`, or (in the future) start the server with `evennia start -l`.

## Check your Requirements

Any system that supports Python3.9+ should work. We'll describe how to install
everything in the following sections.
- Linux/Unix
- Windows (Win7, Win8, Win10, Win11)
- Mac OSX (>10.5 recommended)

- [Python](https://www.python.org) (v3.9, 3.10  and 3.11 are tested)
- [Twisted](https://twistedmatrix.com) (v22.0+)
    - [ZopeInterface](https://www.zope.org/Products/ZopeInterface) (v3.0+)  - usually included in Twisted packages
    - Linux/Mac users may need the `gcc` and `python-dev` packages or equivalent.
    - Windows users need [MS Visual C++](https://aka.ms/vs/16/release/vs_buildtools.exe) and *maybe* [pypiwin32](https://pypi.python.org/pypi/pypiwin32).
- [Django](https://www.djangoproject.com) (v4.2+), be warned that latest dev version is usually untested with Evennia.
- [GIT](https://git-scm.com/) - version control software used if you want to install the sources
  (but also useful to track your own code) 
  -  Mac users can use the  [git-osx-installer](https://code.google.com/p/git-osx-installer/) or the  [MacPorts version](https://git-scm.com/book/en/Getting-Started-Installing-Git#Installing-on-Mac).

## Confusion of location (GIT installation)

When doing the [Git installation](Installation-Git), some may be confused and install Evennia in the wrong location. After following the instructions (and using a virtualenv), the folder structure should look like this: 

```
muddev/
    evenv/
    evennia/
    mygame/
```

The evennia code itself is found inside `evennia/evennia/` (so two levels down). Your settings file 
is `mygame/server/conf/settings.py` and the _parent_ setting file is `evennia/evennia/settings_default.py`.

## Virtualenv setup fails 

When doing the `python3.11 -m venv evenv` step, some users report getting an error; something like:

    Error: Command '['evenv', '-Im', 'ensurepip', '--upgrade', '--default-pip']' 
    returned non-zero exit status 1

You can solve this by installing the `python3.11-venv` package or equivalent for your OS. Alternatively you can bootstrap it in this way: 

    python3.11 -m --without-pip evenv

This should set up the virtualenv without `pip`. Activate the new virtualenv and then install pip from within it:

    python -m ensurepip --upgrade

If that fails, a worse alternative to try is 

    curl https://bootstrap.pypa.io/get-pip.py | python3.10    (linux/unix/WSL only)

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
- Some users trying to set up a virtualenv on an NTFS filesystem find that it fails due to issues
  with symlinks not being supported. Answer is to not use NTFS (seriously, why would you do that to  yourself?)

## Mac Troubleshooting

- Some Mac users have reported not being able to connect to `localhost` (i.e. your own computer). If  so, try to connect to `127.0.0.1` instead, which is the same thing. Use port 4000 from mud clients  and port 4001 from the web browser as usual.

## Windows Troubleshooting

- Install Python [from the Python homepage](https://www.python.org/downloads/windows/). You will  need to be a Windows Administrator to install packages. 
- When installing Python, make sure to check-mark *all* install options, especially the one about making Python  available on the path (you may have to scroll to see it). This allows you to
  just write `python` in any console without first finding where the `python`   program actually sits on your hard drive.
- If you get a `command not found` when trying to run the `evennia` program after installation, try closing the   Console and starting it again (remember to re-activate the virtualenv if you use one!). Sometimes Windows is not updating its environment properly and `evennia` will be available only in the new console.
- If you installed Python but the `python` command is not available (even in a new console), then
  you might have missed installing Python on the path. In the Windows Python installer you get a list  of options for what to install. Most or all options are pre-checked except this one, and you may  even have to scroll down to see it. Reinstall Python and make sure it's checked.
- If your MUD client cannot connect to `localhost:4000`, try the equivalent `127.0.0.1:4000`
  instead. Some MUD clients on Windows does not appear to understand the alias `localhost`.
- Some Windows users get an error installing the Twisted 'wheel'. A wheel is a pre-compiled binary
  package for Python. A common reason for this error is that you are using a 32-bit version of Python,  but Twisted has not yet uploaded the latest 32-bit wheel. Easiest way to fix this is to install a  slightly older Twisted version. So if, say, version `22.1` failed, install `22.0` manually with `pip install twisted==22.0`. Alternatively you could check that you are using the 64-bit version of Python  and uninstall any 32bit one. If so, you must then `deactivate` the virtualenv, delete the `evenv` folder   and recreate it anew with your new Python.
- If your server won't start, with no error messages (and no log files at all when starting from
  scratch), try to start with `evennia ipstart` instead. If you then see an error about `system cannot find the path specified`, it may be that the file `evennia\evennia\server\twistd.bat` has the wrong path to the `twistd` executable. This file is auto-generated, so try to delete it and then run `evennia start` to rebuild it and see if it works. If it still doesn't work you need to open it in a  text editor like Notepad. It's just one line containing  the path to the `twistd.exe` executable as  determined by Evennia. If you installed Twisted in a non-standard location this might be wrong and  you should update the line to the real location.
- Some users have reported issues with Windows WSL and anti-virus software during Evennia
  development. Timeout errors and the inability to run `evennia connections` may be due to your anti-virus software interfering. Try disabling or changing your anti-virus software settings.
