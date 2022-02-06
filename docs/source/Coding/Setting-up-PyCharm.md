# Setting up PyCharm with Evennia

[PyCharm](https://www.jetbrains.com/pycharm/) is a Python developer's IDE from Jetbrains available
for Windows, Mac and Linux. It is a commercial product but offer free trials, a scaled-down
community edition and also generous licenses for OSS projects like Evennia.

> This page was originally tested on Windows (so use Windows-style path examples), but should work
the same for all platforms.

First, install Evennia on your local machine with [[Getting Started]]. If you're new to PyCharm,
loading your project is as easy as selecting the `Open` option when PyCharm starts, and browsing to
your game folder (the one created with `evennia --init`). We refer to it as `mygame` here.

If you want to be able to examine evennia's core code or the scripts inside your virtualenv, you'll
need to add them to your project too:
1. Go to `File > Open...`
1. Select the folder (i.e. the `evennia` root)
1. Select "Open in current window" and "Add to currently opened projects"

## Setting up the project interpreter

It's a good idea to do this before attempting anything further. The rest of this page assumes your
project is already configured in PyCharm.

1. Go to `File > Settings... > Project: \<mygame\> > Project Interpreter`
1. Click the Gear symbol `> Add local`
1. Navigate to your `evenv/scripts directory`, and select Python.exe

Enjoy seeing all your imports checked properly, setting breakpoints, and live variable watching!

## Attaching PyCharm debugger to Evennia

1. Launch Evennia in your preferred way (usually from a console/terminal)
1. Open your project in PyCharm
1. In the PyCharm menu, select `Run > Attach to Local Process...`
1. From the list, pick the `twistd` process with the `server.py` parameter (Example: `twistd.exe
--nodaemon --logfile=\<mygame\>\server\logs\server.log --python=\<evennia
repo\>\evennia\server\server.py`)

Of course you can attach to the `portal` process as well.  If you want to debug the Evennia launcher
or runner for some reason (or just learn how they work!), see Run Configuration below.

> NOTE: Whenever you reload Evennia, the old Server process will die and a new one start. So when
you restart you have to detach from the old and then reattach to the new process that was created.

> To make the process less tedious you can apply a filter in settings to show only the server.py
process in the list. To do that navigate to: `Settings/Preferences | Build, Execution, Deployment |
Python Debugger` and then in `Attach to process` field put in: `twistd.exe" --nodaemon`. This is an
example for windows, I don't have a working mac/linux box.
![Example process filter configuration](https://i.imgur.com/vkSheR8.png)

## Setting up an Evennia run configuration

This configuration allows you to launch Evennia from inside PyCharm. Besides convenience, it also
allows suspending and debugging the evennia_launcher or evennia_runner at points earlier than you
could by running them externally and attaching. In fact by the time the server and/or portal are
running the launcher will have exited already.

1. Go to `Run > Edit Configutations...`
1. Click the plus-symbol to add a new configuration and choose Python
1. Add the script: `\<yourrepo\>\evenv\Scripts\evennia_launcher.py` (substitute your virtualenv if
it's not named `evenv`)
1. Set script parameters to: `start -l` (-l enables console logging)
1. Ensure the chosen interpreter is from your virtualenv
1. Set Working directory to your `mygame` folder (not evenv nor evennia)
1. You can refer to the PyCharm documentation for general info, but you'll want to set at least a
config name (like "MyMUD start" or similar).

Now set up a "stop" configuration by following the same steps as above, but set your Script
parameters to: stop (and name the configuration appropriately).

A dropdown box holding your new configurations should appear next to your PyCharm run button.
Select MyMUD start and press the debug icon to begin debugging.  Depending on how far you let the
program run, you may need to run your "MyMUD stop" config to actually stop the server, before you'll
be able start it again.

## Alternative run configuration - utilizing logfiles as source of data

This configuration takes a bit different approach as instead of focusing on getting the data back
through logfiles. Reason for that is this way you can easily separate data streams, for example you
rarely want to follow both server and portal at the same time, and this will allow it. This will
also make sure to stop the evennia before starting it, essentially working as reload command (it
will also include instructions how to disable that part of functionality). We will start by defining
a configuration that will stop evennia. This assumes that `upfire` is your pycharm project name, and
also the game name, hence the `upfire/upfire` path.

1. Go to `Run > Edit Configutations...`\
1. Click the plus-symbol to add a new configuration and choose the python interpreter to use (should
be project default)
1. Name the configuration as "stop evennia" and fill rest of the fields accordingly to the image:
![Stop run configuration](https://i.imgur.com/gbkXhlG.png)
1. Press `Apply`

Now we will define the start/reload command that will make sure that evennia is not running already,
and then start the server in one go.
1. Go to `Run > Edit Configutations...`\
1. Click the plus-symbol to add a new configuration and choose the python interpreter to use (should
be project default)
1. Name the configuration as "start evennia" and fill rest of the fields accordingly to the image:
![Start run configuration](https://i.imgur.com/5YEjeHq.png)
1. Navigate to the `Logs` tab and add the log files you would like to follow. The picture shows
adding `portal.log` which will show itself in `portal` tab when running:
![Configuring logs following](https://i.imgur.com/gWYuOWl.png)
1. Skip the following steps if you don't want the launcher to stop evennia before starting.
1. Head back to `Configuration` tab and press the `+` sign at the bottom, under `Before launch....`
and select `Run another configuration` from the submenu that will pop up.
1. Click `stop evennia` and make sure that it's added to the list like on the image above.
1. Click `Apply` and close the run configuration window.

You are now ready to go, and if you will fire up `start evennia` configuration you should see
following in the bottom panel:
![Example of running alternative configuration](https://i.imgur.com/nTfpC04.png)
and you can click through the tabs to check appropriate logs, or even the console output as it is
still running in interactive mode.