# Setting up PyCharm with Evennia

[PyCharm](https://www.jetbrains.com/pycharm/) is a Python developer's IDE from Jetbrains available for Windows, Mac and Linux. 
It is a commercial product but offer free trials, a scaled-down community edition and also generous licenses for OSS projects like Evennia.

First, download and install the IDE edition of your choosing.
The community edition should have everything you need, 
but the professional edition has integrated support for Django which can help.

## From an existing project

First, ensure you have completed the steps outlined [here](https://www.evennia.com/docs/latest/Setup/Installation.html#requirements)
Especially the virtualenv part, this will make setting the IDE up much easier.

1. Open Pycharm and click on the open button, open your root folder corresponding to `mygame/`.
2. Click on File -> Settings -> Project -> Python Interpreter -> Add Interpreter -> Add Local Interpreter
![Example](https://imgur.com/QRo8O1C.png)
3. Click on VirtualEnv -> Existing Interpreter -> Select your existing `evenv` folder and click ok
![Example](https://imgur.com/XDmgjTw.png)

## From a new project


1. Click on the new project button.
2. Select the location for your project.
You should create two new folders, one for the root of your project and one
for the evennia game directly. It should look like `/location/projectfolder/gamefolder`
3. Select the `Custom environment` interpreter type, using `Generate New` of type `Virtual env` using a
compatible base python version as recommended in https://www.evennia.com/docs/latest/Setup/Installation.html#requirements
Then choose a folder for your virtual environment as a sub folder of your project folder.

![Example new project configuration](https://imgur.com/R5Yr9I4.png)

Click on the create button and it will take you inside your new project with a bare bones virtual environment.
To install Evennia, you can then either clone evennia in your project folder or install it via pip.
The simplest way is to use pip.

Click on the `terminal` button

![Terminal Button](https://i.imgur.com/fDr4nhv.png)

1. Type in `pip install evennia`
2. Close the IDE and navigate to the project folder
3. Rename the game folder to a temporary name and create a new empty folder with the previous name
4. Open your OS terminal, navigate to your project folder and activate your virtualenv.
On linux, `source .evenv/bin/activate`
On windows, `evenv\Scripts\activate`
5. Type in `evennia --init mygame`
6. Move the files from your temporary folder, which should contain the `.idea/` folder into
the folder you have created at step 3 and delete the now empty temporary folder.
7. In the terminal, Move into the folder and type in `evennia migrate`
8. Start evennia to ensure that it works with `evennia start` and stop it with `evennia stop`

At this point, you can reopen your IDE and it should be functional.
[Look here for additional information](https://www.evennia.com/docs/latest/Setup/Installation.html)


## Debug Evennia from inside PyCharm

### Attaching to the process
1. Launch Evennia in the pycharm terminal
2. Attempt to start it twice, this will give you the process ID of the server
3. In the PyCharm menu, select `Run > Attach to Process...`
4. From the list, pick the corresponding process id, it should be the `twistd` process with the `server.py` parameter (Example: `twistd.exe --nodaemon --logfile=\<mygame\>\server\logs\server.log --python=\<evennia repo\>\evennia\server\server.py`)

You can attach to the `portal` process as well, if you want to debug the Evennia launcher
or runner for some reason (or just learn how they work!), see Run Configuration below.

> NOTE: Whenever you reload Evennia, the old Server process will die and a new one start. So when you restart you have to detach from the old and then reattach to the new process that was created.


### Run Evennia with a Run/Debug Configuration

This configuration allows you to launch Evennia from inside PyCharm. Besides convenience, it also allows suspending and debugging the evennia_launcher or evennia_runner at points earlier than you could by running them externally and attaching. In fact by the time the server and/or portal are running the launcher will have exited already.

#### On Windows
1. Go to `Run > Edit Configutations...`
2. Click the plus-symbol to add a new configuration and choose Python
3. Add the script: `\<yourprojectfolder>\.venv\Scripts\evennia_launcher.py` (substitute your virtualenv if it's not named `evenv`)
4. Set script parameters to: `start -l` (-l enables console logging)
5. Ensure the chosen interpreter is your virtualenv
6. Set Working directory to your `mygame` folder (not your project folder nor evennia)
7. You can refer to the PyCharm documentation for general info, but you'll want to set at least a config name (like "MyMUD start" or similar).

A dropdown box holding your new configurations should appear next to your PyCharm run button. 
Select it start and press the debug icon to begin debugging.

#### On Linux
1. Go to `Run > Edit Configutations...`
2. Click the plus-symbol to add a new configuration and choose Python
3. Add the script: `/<yourprojectfolder>/.venv/bin/twistd` (substitute your virtualenv if it's not named `evenv`)
4. Set script parameters to: `--python=/<yourprojectfolder>/.venv/lib/python3.11/site-packages/evennia/server/server.py --logger=evennia.utils.logger.GetServerLogObserver --pidfile=/<yourprojectfolder>/<yourgamefolder>/server/server.pid --nodaemon`
5. Add an environment variable `DJANGO_SETTINGS_MODULE=server.conf.settings`
6. Ensure the chosen interpreter is your virtualenv
7. Set Working directory to your game folder (not your project folder nor evennia)
8. You can refer to the PyCharm documentation for general info, but you'll want to set at least a config name (like "MyMUD start" or similar).

A dropdown box holding your new configurations should appear next to your PyCharm run button. 
Select it start and press the debug icon to begin debugging.
Note that this only starts the server process, you will still need to start the portal
using evennia start AFTER launching the server process.

### Alternative config - utilizing logfiles as source of data

This configuration takes a bit different approach as instead of focusing on getting the data back through logfiles. Reason for that is this way you can easily separate data streams, for example you rarely want to follow both server and portal at the same time, and this will allow it. This will also make sure to stop the evennia before starting it, essentially working as reload command (it will also include instructions how to disable that part of functionality). We will start by defining a configuration that will stop evennia. This assumes that `upfire` is your pycharm project name, and also the game name, hence the `upfire/upfire` path.

1. Go to `Run > Edit Configutations...`\
1. Click the plus-symbol to add a new configuration and choose the python interpreter to use (should be project default)
1. Name the configuration as "stop evennia" and fill rest of the fields accordingly to the image:
![Stop run configuration](https://i.imgur.com/gbkXhlG.png)
1. Press `Apply`

Now we will define the start/reload command that will make sure that evennia is not running already, and then start the server in one go.
1. Go to `Run > Edit Configutations...`\
1. Click the plus-symbol to add a new configuration and choose the python interpreter to use (should be project default)
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