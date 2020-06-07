# Installing on Android


This page describes how to install and run the Evennia server on an Android phone. This will involve
installing a slew of third-party programs from the Google Play store, so make sure you are okay with
this before starting.

## Install Termux

The first thing to do is install a terminal emulator that allows a "full" version of linux to be run. Note that Android is essentially running on top of linux so if you have a rooted phone, you may be able to skip this step. You *don't* require a rooted phone to install Evennia though.

Assuming we do not have root, we will install [Termux](https://play.google.com/store/apps/details?id=com.termux&hl=en).
Termux provides a base installation of Linux essentials, including apt and Python, and makes them available under a writeable directory. It also gives us a terminal where we can enter commands. By default, Android doesn't give you permissions to the root folder, so Termux pretends that its own installation directory is the root directory.

Termux will set up a base system for us on first launch, but we will need to install some prerequisites for Evennia. Commands you should run in Termux will look like this:

```
$ cat file.txt
```
The `$` symbol is your prompt - do not include it when running commands.

## Prerequisites

To install some of the libraries Evennia requires, namely Pillow and Twisted, we have to first install some packages they depend on. In Termux, run the following 
```
$ pkg install -y clang git zlib ndk-sysroot libjpeg-turbo libcrypt python
```

Termux ships with Python 3, perfect. Python 3 has venv (virtualenv) and pip (Python's module installer) built-in.

So, let's set up our virtualenv. This keeps the Python packages we install separate from the system versions.

```
$ cd
$ python3 -m venv evenv
```

This will create a new folder, called `evenv`, containing the new python executable.
Next, let's activate our new virtualenv. Every time you want to work on Evennia, you need to run the following command:

```
$ source evenv/bin/activate
```

Your prompt will change to look like this:
```
(evenv) $
```
Update the updaters and installers in the venv: pip, setuptools and wheel.
```
python3 -m pip install --upgrade pip setuptools wheel
```

### Installing Evennia

Now that we have everything in place, we're ready to download and install Evennia itself.

Mysterious incantations
```
export LDFLAGS="-L/data/data/com.termux/files/usr/lib/"
export CFLAGS="-I/data/data/com.termux/files/usr/include/"
```
(these tell clang, the C compiler, where to find the bits for zlib when building Pillow)

Install the latest Evennia in a way that lets you edit the source
```
(evenv) $ pip install --upgrade -e 'git+https://github.com/evennia/evennia#egg=evennia' 
```

This step will possibly take quite a while - we are downloading Evennia and are then installing it, building all of the requirements for Evennia to run. If you run into trouble on this step, please see [Troubleshooting](Installing-on-Android#troubleshooting).

You can go to the dir where Evennia is installed with `cd $VIRTUAL_ENV/src/evennia`. `git grep (something)` can be handy, as can `git diff`

### Final steps

At this point, Evennia is installed on your phone! You can now continue with the original [Getting Started](Getting-Started) instruction, we repeat them here for clarity.

To start a new game:

```
(evenv) $ evennia --init mygame
(evenv) $ ls
mygame evenv
```

To start the game for the first time:

```
(evenv) $ cd mygame
(evenv) $ evennia migrate
(evenv) $ evennia start
```

Your game should now be running! Open a web browser at http://localhost:4001 or point a telnet client to localhost:4000 and log in with the user you created.

## Running Evennia

When you wish to run Evennia, get into your Termux console and make sure you have activated your virtualenv as well as are in your game's directory. You can then run evennia start as normal.

```
$ cd ~ && source evenv/bin/activate
(evenv) $ cd mygame
(evenv) $ evennia start
```

You may wish to look at the [Linux Instructions](Getting-Started#linux-install) for more.

## Caveats

- Android's os module doesn't support certain functions - in particular getloadavg. Thusly, running the command @server in-game will throw an exception. So far, there is no fix for this problem.
- As you might expect, performance is not amazing.
- Android is fairly aggressive about memory handling, and you may find that your server process is killed if your phone is heavily taxed. Termux seems to keep a notification up to discourage this.

## Troubleshooting

As time goes by and errors are reported, this section will be added to.

Some steps to try anyway:
* Make sure your packages are up-to-date, try running `pkg update && pkg upgrade -y`
* Make sure you've installed the clang package. If not, try `pkg install clang -y`
* Make sure you're in the right directory. `cd ~/mygame
* Make sure you've sourced your virtualenv. type `cd && source evenv/bin/activate`
* See if a shell will start: `cd ~/mygame ; evennia shell`
* Look at the log files in ~/mygame/server/logs/