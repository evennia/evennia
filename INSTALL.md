
# Evennia installation

The latest and more detailed installation instructions can be found
[here](https://github.com/evennia/evennia/wiki/Getting-Started).

## Installing Python

First install [Python](https://www.python.org/). Linux users should
have it in their repositories, Windows/Mac users can get it from the
Python homepage. You need the 2.7.x version (Python 3 is not yet
supported). Windows users, make sure to select the option to make
Python available in your path - this is so you can call it everywhere
as `python`. Python 2.7.9 and later also includes the
[pip](https://pypi.python.org/pypi/pip/) installer out of the box,
otherwise install this separately (in linux it's usually found as the
`python-pip` package).

### installing virtualenv

This step is optional, but *highly* recommended. For installing
up-to-date Python packages we recommend using
[virtualenv](https://pypi.python.org/pypi/virtualenv), this makes it
easy to keep your Python packages up-to-date without interfering with
the defaults for your system.

```
pip install virtualenv
```

Go to the place where you want to make your virtual python library
storage. This does not need to be near where you plan to install
Evennia. Then do

```
virtualenv vienv
```

A new folder `vienv` will be created (you could also name it something
else if you prefer). Activate the virtual environment like this:

```
# for Linux/Unix/Mac:
source vienv/bin/activate
# for Windows:
vienv\Scripts\activate.bat
```

You should see `(vienv)` next to your prompt to show you the
environment is active. You need to activate it whenever you open a new
terminal, but you *don't* have to be inside the `vienv` folder henceforth.


## Get the developer's version of Evennia

This is currently the only Evennia version available. First download
and install [Git](http://git-scm.com/) from the homepage or via the
package manager in Linux. Next, go to the place where you want the
`evennia` folder to be created and run

```
git clone https://github.com/evennia/evennia.git
```

If you have a github account and have [set up SSH
keys](https://help.github.com/articles/generating-ssh-keys/), you want
to use this instead:

```
git clone git@github.com:evennia/evennia.git
```

In the future you just enter the new `evennia` folder and do

```
git pull
```

to get the latest Evennia updates.

## Evennia package install

Stand at the root of your new `evennia` directory and run

```
pip install -e .
```

(note the period "." at the end, this tells pip to install from the
current directory). This will install Evennia and all its dependencies
(into your virtualenv if you are using that) and make the `evennia`
command available on the command line. You can find Evennia's
dependencies in `evennia/requirements.txt`.

## Creating your game project

To create your new game you need to initialize a new game project.
This should be done somewhere *outside* of your `evennia` folder.


```
evennia --init mygame
```

This will create a new game project named "mygame" in a folder of the
same name. If you want to change the settings for your project, you
will need to edit `mygame/server/conf/settings.py`.


## Starting Evennia

Enter your new game directory and run

```
evennia migrate
evennia start
```

Follow the instructions to create your superuser account. A lot of
information will scroll past as the database is created and the server
initializes. After this Evennia will be running. Use

```
evennia -h
```

for help with starting, stopping and other operations.

Start up your MUD client of choice and point it to your server and
port *4000*.  If you are just running locally the server name is
*localhost*.

Alternatively, you can find the web interface and webclient by
pointing your web browser to *http://localhost:4001*.

Finally, login with the superuser account and password you provided
earlier.  Welcome to Evennia!
