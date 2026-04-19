# Installation

Evennia requires having [Python](https://www.python.org/downloads/) and pip installed. The current recommended versions are 3.12 or 3.13.

```{note}
As this is not a Python installation guide, please consult the instructions for installing Python+pip for your operating system if it is not already installed.
```

## Quickstart

Make sure you have a supported Python version installed, navigate to your development directory in a terminal, and execute the following commands appropriate for your operating system.

#### Linux/Mac

    $ python -m venv evenv
    $ source evenv/bin/activate
    $ pip install evennia

#### Windows

    py -m venv evenv
    .\evenv\lib\activate
    pip install evennia
    py -m evennia

## Alternative Installations

If you have specific install environment needs that differ from the standard instructions, the following additional guides are available:

- [Docker](./Installation-Docker.md)
- [Git](./Installation-Git.md)
- [Android](./Installation-Android.md)
- [Upgrading from a beta version of Evennia](./Installation-Upgrade.md)

## Install Guide

### 1. Set up a development environment

You will need to install Evennia to a *python virtual environment*, so the first step is to create one. This is done using the `venv` package in python:

    $ python -m venv evenv

```{note}
**Windows Only**: The recommended way to run python from the Windows command line is the `py` launcher command, so you will most likely want to use `py` instead of `python` here and for the rest of the instructions. However, you can also directly reference the python version. Consult the official [Python on Windows](https://docs.python.org/3/faq/windows.html) documentation for more information.
```
    
This will create a new directory named `evenv` containing the *virtual environment* - a set of python packages and executables installed locally, rather than system-wide. Doing this prevents permissions and conflict issues later.

Once it's created, you *activate* it in order to use that environment - it'll keep the python version and anything you install via `pip` contained within it.

Linux/Mac:

    $ source evenv/bin/activate

Windows:

    .\evenv\lib\activate


You'll need to do this step - activating the environment - every time you open a new terminal to work on your Evennia game.

### 2. Install Evennia

Once your virtual environment is activated, you can install Evennia into it:

    pip install evennia


This will install the latest release version of Evennia into your virtual environment.


If you use a [contrib](../Contribs/Contribs-Overview.md) that warns you that it needs additional packages, use the following to install all of the extra dependencies:

    pip install evennia[extra]

```{note}
**Windows only**: After installing, you will need to enter one more command - `py -m evennia` - to make sure that the `evennia` command is available in your terminal.
```

### 3. Upgrading Evennia

To update to a new release of Evennia, first ensure your same virtual environment is active, then run the upgrade install command:

    pip install --upgrade evennia

This will upgrade evennia and all its dependencies to the latest version. If you used the extra dependencies installation, just add it to the end to upgrade those as well:

    pip install --upgrade evennia[extra]

## Next Steps

That's it! Check out the guide for [setting up a new game](./Creating-Game-Dir.md) to get started developing!
