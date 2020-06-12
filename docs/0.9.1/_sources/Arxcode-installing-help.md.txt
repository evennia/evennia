# Arxcode installing help

## Introduction 

[Arx - After the Reckoning](http://play.arxmush.org/) is a big and very popular
[Evennia](http://www.evennia.com)-based game. Arx is heavily roleplaying-centric, relying on game
masters to drive the story. Technically it's maybe best described as "a MUSH, but with more coded
systems". In August of 2018, the game's developer, Tehom, generously released the [source code of
Arx on github](https://github.com/Arx-Game/arxcode). This is a treasure-trove for developers wanting
to pick ideas or even get a starting game to build on. These instructions are based on the Arx-code
released as of *Aug 12, 2018*.

If you are not familiar with what Evennia is, you can read 
[an introduction here](Evennia-Introduction). 

It's not too hard to run Arx from the sources (of course you'll start with an empty database) but
since part of Arx has grown organically, it doesn't follow standard Evennia paradigms everywhere.
This page covers one take on installing and setting things up while making your new Arx-based game
better match with the vanilla Evennia install. 

## Installing Evennia

Firstly, set aside a folder/directory on your drive for everything to follow. 

You need to start by installing [Evennia](http://www.evennia.com) by following most of the [Getting Started
Instructions](Getting-Started) for your OS. The difference is that you need to `git clone https://github.com/TehomCD/evennia.git` instead of Evennia's repo because Arx uses TehomCD's older Evennia 0.8 [fork](https://github.com/TehomCD/evennia), notably still using Python2. This detail is important if referring to newer Evennia documentation. 

If you are new to Evennia it's *highly* recommended that you run through the
instructions in full - including initializing and starting a new empty game and connecting to it.
That way you can be sure Evennia works correctly as a base line. If you have trouble, make sure to
read the [Troubleshooting instructions](Getting-Started#troubleshooting) for your
operating system. You can also drop into our
[forums](https://groups.google.com/forum/#%21forum/evennia), join `#evennia` on `irc.freenode.net`
or chat from the linked [Discord Server](https://discord.gg/NecFePw). 

After installing you should have a `virtualenv` running and you should have the following file structure in your set-aside folder: 

```
vienv/
evennia/
mygame/

```

Here `mygame` is the empty game you created during the Evennia install, with `evennia --init`. Go to
that and run `evennia stop` to make sure your empty game is not running. We'll instead let Evenna
run Arx, so in principle you could erase `mygame` - but it could also be good to have a clean game
to compare to. 

## Installing Arxcode

### Clone the arxcode repo

Cd to the root of your directory and clone the released source code from github: 

    git clone https://github.com/Arx-Game/arxcode.git myarx 

A new folder `myarx` should appear next to the ones you already had. You could rename this to
something else if you want. 

Cd into `myarx`. If you wonder about the structure of the game dir, you can [read more about it here](Directory-Overview). 

### Clean up settings

Arx has split evennia's normal settings into `base_settings.py` and `production_settings.py`. It
also has its own solution for managing 'secret' parts of the settings file. We'll keep most of Arx
way but remove the secret-handling and replace it with the normal Evennia method. 

Cd into `myarx/server/conf/` and open the file `settings.py` in a text editor. The top part (within
`"""..."""`) is just help text. Wipe everything underneath that and make it look like this instead
(don't forget to save): 

```
from base_settings import *
    
TELNET_PORTS = [4000]
SERVERNAME = "MyArx"
GAME_SLOGAN = "The cool game"

try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
```

> Note: Indents and capitalization matter in Python. Make indents 4 spaces (not tabs) for your own
> sanity. If you want a starter on Python in Evennia, [you can look here](Python-basic-introduction).

This will import Arx' base settings and override them with the Evennia-default telnet port and give
the game a name. The slogan changes the sub-text shown under the name of your game in the website
header. You can tweak these to your own liking later.

Next, create a new, empty file `secret_settings.py` in the same location as the `settings.py` file.
This can just contain the following: 

```python
SECRET_KEY = "sefsefiwwj3 jnwidufhjw4545_oifej whewiu hwejfpoiwjrpw09&4er43233fwefwfw"

```

Replace the long random string with random ASCII characters of your own. The secret key should not
be shared. 

Next, open `myarx/server/conf/base_settings.py` in your text editor. We want to remove/comment out
all mentions of the `decouple` package, which Evennia doesn't use (we use `private_settings.py` to
hide away settings that should not be shared). 

Comment out `from decouple import config` by adding a `#` to the start of the line: `# from decouple
import config`. Then search for `config(` in the file and comment out all lines where this is used.
Many of these are specific to the server environment where the original Arx runs, so is not that
relevant to us. 

### Install Arx dependencies 

Arx has some further dependencies beyond vanilla Evennia. Start by `cd`:ing to the root of your
`myarx` folder. 

> If you run *Linux* or *Mac*: Edit `myarx/requirements.txt` and comment out the line
> `pypiwin32==219` - it's only needed on Windows and will give an error on other platforms.  

Make sure your `virtualenv` is active, then run

    pip install -r requirements.txt

The needed Python packages will be installed for you. 

### Adding logs/ folder

The Arx repo does not contain the `myarx/server/logs/` folder Evennia expects for storing server
logs. This is simple to add: 

    # linux/mac
    mkdir server/logs
    # windows
    mkdir server\logs

### Setting up the database and starting

From the `myarx` folder, run 

    evennia migrate

This creates the database and will step through all database migrations needed.

    evennia start

If all goes well Evennia will now start up, running Arx! You can connect to it on `localhost` (or
`127.0.0.1` if your platform doesn't alias `localhost`), port `4000` using a Telnet client.
Alternatively, you can use your web browser to browse to `http://localhost:4001` to see the game's
website and get to the web client. 

When you log in you'll get the standard Evennia greeting (since the database is empty), but you can
try `help` to see that it's indeed Arx that is running.

### Additional Setup Steps

The first time you start Evennia after creating the database with the `evennia migrate` step above,
it should create a few starting objects for you - your superuser account, which it will prompt you
to enter, a starting room (Limbo), and a character object for you. If for some reason this does not
occur, you may have to follow the steps below.  For the first time Superuser login you may have to
run steps 7-8 and 10 to create and connect to your in-came Character. 

1. Login to the game website with your Superuser account.
2. Press the `Admin` button to get into the (Django-) Admin Interface.
3. Navigate to the `Accounts` section.
4. Add a new Account named for the new staffer. Use a place holder password and dummy e-mail
   address.
5. Flag account as `Staff` and apply the `Admin` permission group (This assumes you have already set
   up an Admin Group in Django). 
6. Add Tags named `player` and `developer`. 
7. Log into the game using the web client (or a third-party telnet client) using your superuser
   account. Move to where you want the new staffer character to appear. 
8. In the game client, run `@create/drop <staffername>:typeclasses.characters.Character`, where
   `<staffername>` is usually the same name you used for the Staffer account you created in the
   Admin earlier (if you are creating a Character for your superuser, use your superuser account name).
   This creates a new in-game Character and places it in your current location.
9. Have the new Admin player log into the game.
10. Have the new Admin puppet the character with `@ic StafferName`. 
11. Have the new Admin change their password - `@password <old password> = <new password>`.

Now that you have a Character and an Account object, there's a few additional things you may need to
do in order for some commands to function properly. You can either execute these as in-game commands
while `@ic` (controlling your character object).

1. `@py from web.character.models import RosterEntry;RosterEntry.objects.create(player=self.player, character=self)`
2. `@py from world.dominion.models import PlayerOrNpc, AssetOwner;dompc = PlayerOrNpc.objects.create(player = self.player);AssetOwner.objects.create(player=dompc)`

Those steps will give you a 'RosterEntry', 'PlayerOrNpc', and 'AssetOwner' objects. RosterEntry
explicitly connects a character and account object together, even while offline, and contains
additional information about a character's current presence in game (such as which 'roster' they're
in, if you choose to use an active roster of characters). PlayerOrNpc are more character extensions,
as well as support for npcs with no in-game presence and just represented by a name which can be
offscreen members of a character's family. It also allows for membership in Organizations.
AssetOwner holds information about a character or organization's money and resources.

## Alternate guide by Pax for installing on Windows

If for some reason you cannot use the Windows Subsystem for Linux (which would use instructions identical to the ones above), it's possible to get Evennia running under Anaconda for Windows. The process is a little bit trickier.

 Make sure you have:
 * Git for Windows               https://git-scm.com/download/win
 * Anaconda for Windows          https://www.anaconda.com/distribution/
 * VC++ Compiler for Python 2.7  http://aka.ms/vcpython27

conda update conda
conda create -n arx python=2.7
source activate arx

 Set up a convenient repository place for things.

cd ~
mkdir Source
cd Source
mkdir Arx
cd Arx

 Replace the SSH git clone links below with your own github forks. 
 If you don't plan to change Evennia at all, you can use the 
 evennia/evennia.git repo instead of a forked one.

git clone git@github.com:<youruser>/evennia.git
git clone git@github.com:<youruser>/arxcode.git

 Evennia is a package itself, so we want to install it and all of its 
 prerequisites, after switching to the appropriately-tagged branch for
 Arxcode.

cd evennia
git checkout tags/v0.7 -b arx-master
pip install -e .

 Arx has some dependencies of its own, so now we'll go install them
 As it is not a package, we'll use the normal requirements file.

cd ../arxcode
pip install -r requirements.txt

 The git repo doesn't include the empty log directory and Evennia is unhappy if you
 don't have it, so while still in the arxcode directory... 

mkdir server/logs

 Now hit https://github.com/evennia/evennia/wiki/Arxcode-installing-help and
 change the setup stuff as in the 'Clean up settings' section.

 Then we will create our default database...

../evennia/bin/windows/evennia.bat migrate

 ...and do the first run. You need winpty because Windows does not have a TTY/PTY
 by default, and so the Python console input commands (used for prompts on first
 run) will fail and you will end up in an unhappy place. Future runs, you should
 not need winpty.

winpty ../evennia/bin/windows/evennia.bat start

 Once this is done, you should have your Evennia server running Arxcode up
 on localhost at port 4000, and the webserver at http://localhost:4001/

 And you are done! Huzzah!