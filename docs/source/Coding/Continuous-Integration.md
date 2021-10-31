# Continuous Integration

One of the advantages of Evennia over traditional MUSH development systems is that Evennia is
capable of integrating into enterprise level integration environments and source control. Because of
this, it can also be the subject of automation for additional convenience, allowing a more
streamlined development environment.

## What is Continuous Integration?

[Continuous Integration (CI)](https://www.thoughtworks.com/continuous-integration) is a development
practice that requires developers to integrate code into a shared repository several times a day.
Each check-in is then verified by an automated build, allowing teams to detect problems early.

For Evennia, continuous integration allows an automated build process to:
* Pull down a latest build from Source Control.
* Run migrations on the backing SQL database.
* Automate additional unique tasks for that project.
* Run unit tests.
* Publish those files to the server directory
* Reload the game.

## Preparation
To prepare a CI environment for your `MU*`, it will be necessary to set up some prerequisite
software for your server.

Among those you will need:
* A Continuous Integration Environment.
  * I recommend [TeamCity](https://www.jetbrains.com/teamcity/) which has an in-depth [Setup
Guide](https://confluence.jetbrains.com/display/TCD8/Installing+and+Configuring+the+TeamCity+Server)
* [Source Control](./Version-Control.md)
  * This could be Git or SVN or any other available SC.

## Linux TeamCity Setup
For this part of the guide, an example setup will be provided for administrators running a TeamCity
build integration environment on Linux. 

After meeting the preparation steps for your specific environment, log on to your teamcity interface
at `http://<your server>:8111/`.

Create a new project named "Evennia" and in it construct a new template called continuous-
integration.

### A Quick Overview
Templates are fancy objects in TeamCity that allow an administrator to define build steps that are
shared between one or more build projects. Assigning a VCS Root (Source Control) is unnecessary at
this stage, primarily you'll be worrying about the build steps and your default parameters (both
visible on the tabs to the left.)

### Template Setup

In this template, you'll be outlining the steps necessary to build your specific game. (A number of
sample scripts are provided under this section below!) Click Build Steps and prepare your general
flow. For this example, we will be doing a few basic example steps:

* Transforming the Settings.py file
  * We do this to update ports or other information that make your production environment unique
    from your development environment.
* Making migrations and migrating the game database.
* Publishing the game files.
* Reloading the server.

For each step we'll being use the "Command Line Runner" (a fancy name for a shell script executor).

* Create a build step with the name: Transform Configuration
* For the script add:    

    ```bash
    #!/bin/bash
    # Replaces the game configuration with one 
    # appropriate for this deployment.
    
    CONFIG="%system.teamcity.build.checkoutDir%/server/conf/settings.py"
    MYCONF="%system.teamcity.build.checkoutDir%/server/conf/my.cnf"
    
    sed -e 's/TELNET_PORTS = [4000]/TELNET_PORTS = [%game.ports%]/g' "$CONFIG" > "$CONFIG".tmp && mv
"$CONFIG".tmp "$CONFIG"
    sed -e 's/WEBSERVER_PORTS = [(4001, 4002)]/WEBSERVER_PORTS = [%game.webports%]/g' "$CONFIG" >
"$CONFIG".tmp && mv "$CONFIG".tmp "$CONFIG"
    
    # settings.py MySQL DB configuration
    echo Configuring Game Database...
    echo "" >> "$CONFIG"
    echo "######################################################################" >> "$CONFIG"
    echo "# MySQL Database Configuration" >> "$CONFIG"
    echo "######################################################################" >> "$CONFIG"
    
    echo "DATABASES = {" >> "$CONFIG"
    echo "   'default': {" >> "$CONFIG"
    echo "       'ENGINE': 'django.db.backends.mysql'," >> "$CONFIG"
    echo "       'OPTIONS': {" >> "$CONFIG"
    echo "           'read_default_file': 'server/conf/my.cnf'," >> "$CONFIG"
    echo "       }," >> "$CONFIG"
    echo "   }" >> "$CONFIG"
    echo "}" >> "$CONFIG"
    
    # Create the My.CNF file.
    echo "[client]" >> "$MYCONF"
    echo "database = %mysql.db%" >> "$MYCONF"
    echo "user = %mysql.user%" >> "$MYCONF"
    echo "password = %mysql.pass%" >> "$MYCONF"
    echo "default-character-set = utf8" >> "$MYCONF"
    ```

If you look at the parameters side of the page after saving this script, you'll notice that some new
parameters have been populated for you. This is because we've included new teamcity configuration
parameters that are populated when the build itself is ran. When creating projects that inherit this
template, we'll be able to fill in or override those parameters for project-specific configuration.

* Go ahead and create another build step called "Make Database Migration"
  * If you're using SQLLite on your game, it will be prudent to change working directory on this
step to: %game.dir%
* In this script include:

    ```bash
    #!/bin/bash
    # Update the DB migration
    
    LOGDIR="server/logs"
    
    . %evenv.dir%/bin/activate
    
    # Check that the logs directory exists.
    if [ ! -d "$LOGDIR" ]; then
      # Control will enter here if $LOGDIR doesn't exist.
      mkdir "$LOGDIR"
    fi
    
    evennia makemigrations
    ```

* Create yet another build step, this time named: "Execute Database Migration":
  * If you're using SQLLite on your game, it will be prudent to change working directory on this
step to: %game.dir%
    ```bash
    #!/bin/bash
    # Apply the database migration.
    
    LOGDIR="server/logs"
    
    . %evenv.dir%/bin/activate
    
    # Check that the logs directory exists.
    if [ ! -d "$LOGDIR" ]; then
      # Control will enter here if $LOGDIR doesn't exist.
      mkdir "$LOGDIR"
    fi
    
    evennia migrate

    ```

Our next build step is where we actually publish our build. Up until now, all work on game has been
done in a 'work' directory on TeamCity's build agent. From that directory we will now copy our files
to where our game actually exists on the local server.

* Create a new build step called "Publish Build":
  * If you're using SQLLite on your game, be sure to order this step ABOVE the Database Migration
steps. The build order will matter!
    ```bash
    #!/bin/bash
    # Publishes the build to the proper build directory.
    
    DIRECTORY="%game.dir%"
    
    if [ ! -d "$DIRECTORY" ]; then
      # Control will enter here if $DIRECTORY doesn't exist.
      mkdir "$DIRECTORY"
    fi
    
    # Copy all the files.
    cp -ruv %teamcity.build.checkoutDir%/* "$DIRECTORY"
    chmod -R 775 "$DIRECTORY"

    ```

Finally the last script will reload our game for us.

* Create a new script called "Reload Game":
  * The working directory on this build step will be: %game.dir%
    ```bash
    #!/bin/bash
    # Apply the database migration.
    
    LOGDIR="server/logs"
    PIDDIR="server/server.pid"
    
    . %evenv.dir%/bin/activate
    
    # Check that the logs directory exists.
    if [ ! -d "$LOGDIR" ]; then
      # Control will enter here if $LOGDIR doesn't exist.
      mkdir "$LOGDIR"
    fi
    
    # Check that the server is running.
    if [ -d "$PIDDIR" ]; then
      # Control will enter here if the game is running.
      evennia reload
    fi
    ```

Now the template is ready for use! It would be useful this time to revisit the parameters page and
set the evenv parameter to the directory where your virtualenv exists: IE "/srv/mush/evenv".

### Creating the Project

Now it's time for the last few steps to set up a CI environment.

* Return to the Evennia Project overview/administration page. 
* Create a new Sub-Project called "Production"
  * This will be the category that holds our actual game.
* Create a new Build Configuration in Production with the name of your MUSH.
  * Base this configuration off of the continuous-integration template we made earlier.
* In the build configuration, enter VCS roots and create a new VCS root that points to the
branch/version control that you are using.
* Go to the parameters page and fill in the undefined parameters for your specific configuration.
* If you wish for the CI to run every time a commit is made, go to the VCS triggers and add one for
"On Every Commit".

And you're done! At this point, you can return to the project overview page and queue a new build
for your game. If everything was set up correctly, the build will complete successfully. Additional
build steps could be added or removed at this point, adding some features like Unit Testing or more!