# Running Evennia in Docker

Evennia has an [official docker image](https://hub.docker.com/r/evennia/evennia/) which makes
running an Evennia-based game in a Docker container easy.

## Install Evennia through docker

First, install the `docker` program so you can run the Evennia container. You can get it freely from
[docker.com](https://www.docker.com/). Linux users can likely also get it through their normal
package manager.

To fetch the latest evennia docker image, run: 

    docker pull evennia/evennia

This is a good command to know, it is also how you update to the latest version when we make updates
in the future. This tracks the `master` branch of Evennia.

> Note: If you want to experiment with the (unstable) `develop` branch, use `docker pull
evennia/evennia:develop`.

Next `cd` to a place where your game dir is, or where you want to create it. Then run: 

    docker run -it --rm -p 4000:4000 -p 4001:4001 -p 4002:4002 --rm -v $PWD:/usr/src/game --user
$UID:$GID evennia/evennia

Having run this (see next section for a description of what's what), you will be at a prompt inside
the docker container:

```bash
evennia|docker /usr/src/game $
```

This is a normal shell prompt. We are in the `/usr/src/game` location inside the docker container.
If you had anything in the folder you started from, you should see it here (with `ls`) since we
mounted the current directory to `usr/src/game` (with `-v` above). You have the `evennia` command
available and can now proceed to create a new game as per the [Getting Started](Getting-Started)
instructions (you can skip the virtualenv and install 'globally' in the container though).

You can run Evennia from inside this container if you want to, it's like you are root in a little
isolated Linux environment. To exit the container and all processes in there, press `Ctrl-D`. If you
created a new game folder, you will find that it has appeared on-disk.

> The game folder or any new files that you created from inside the container will appear as owned
by `root`. If you want to edit the files outside of the container you should change the ownership.
On Linux/Mac you do this with `sudo chown myname:myname -R mygame`, where you replace `myname` with
your username and `mygame` with whatever your game folder is named.

### Description of the `docker run` command

```bash
    docker run -it --rm -p 4000:4000 -p 4001:4001 -p 4002:4002 --rm -v $PWD:/usr/src/game --user
$UID:$GID evennia/evennia
```

This is what it does: 

- `docker run ... evennia/evennia` tells us that we want to run a new container based on the
`evennia/evennia` docker image. Everything in between are options for this. The `evennia/evennia` is
the name of our [official docker image on the dockerhub
repository](https://hub.docker.com/r/evennia/evennia/). If you didn't do `docker pull
evennia/evennia` first, the image will be downloaded when running this, otherwise your already
downloaded version will be used. It contains everything needed to run Evennia.
- `-it` has to do with creating an interactive session inside the container we start.
- `--rm` will make sure to delete the container when it shuts down. This is nice to keep things tidy
on your drive.
- `-p 4000:4000 -p 4001:4001 -p 4002:4002` means that we *map* ports `4000`, `4001` and `4002` from
inside the docker container to same-numbered ports on our host machine. These are ports for telnet,
webserver and websockets. This is what allows your Evennia server to be accessed from outside the
container (such as by your MUD client)!
- `-v $PWD:/usr/src/game` mounts the current directory (*outside* the container) to the path
`/usr/src/game` *inside* the container. This means that when you edit that path in the container you
will actually be modifying the "real" place on your hard drive. If you didn't do this, any changes
would only exist inside the container and be gone if we create a new one. Note that in linux a
shortcut for the current directory is `$PWD`. If you don't have this for your OS, you can replace it
with the full path to the current on-disk directory (like `C:/Development/evennia/game` or wherever
you want your evennia files to appear).
- `--user $UID:$GID` ensures the container's modifications to `$PWD` are done with you user and
group IDs instead of root's IDs (root is the user running evennia inside the container). This avoids
having stale `.pid` files in your filesystem between container reboots which you have to force
delete with `sudo rm server/*.pid` before each boot.

## Running your game as a docker image

If you run the  `docker` command given in the previous section from your game dir you can then
easily start Evennia and have a running server without any further fuss.

But apart from ease of install, the primary benefit to running an Evennia-based game in a container
is  to simplify its deployment into a public production environment. Most cloud-based hosting
providers these days support the ability to run container-based applications. This makes deploying
or updating your game as simple as building a new container image locally, pushing it to your Docker
Hub account, and then pulling from Docker Hub into your AWS/Azure/other docker-enabled hosting
account. The container eliminates the need to install Python, set up a virtualenv, or run pip to
install dependencies.

### Start Evennia and run through docker

For remote or automated deployment you may want to start Evennia immediately as soon as the docker
container comes up. If you already have a game folder with a database set up you can also start the
docker container and pass commands directly to it. The command you pass will be the main process to
run in the container. From your game dir, run for example this command:

    docker run -it --rm -p 4000:4000 -p 4001:4001 -p 4002:4002 --rm -v $PWD:/usr/src/game
evennia/evennia evennia start -l

This will start Evennia as the foreground process, echoing the log to the terminal. Closing the
terminal will kill the server. Note that you *must* use a foreground command like `evennia start -l`
or `evennia ipstart` to start the server - otherwise the foreground process will finish immediately
and the container go down.
### Create your own game image 

These steps assume that you have created or otherwise obtained a game directory already. First, `cd`
to your game dir and create a new empty text file named `Dockerfile`. Save the following two lines
into it:

```
FROM evennia/evennia:latest

ENTRYPOINT evennia start -l
```

These are instructions for building a new docker image. This one is based on the official
`evennia/evennia` image, but also makes sure to start evennia when it runs (so we don't need to
enter it and run commands).

To build the image:

```bash
    docker build -t mydhaccount/mygame .
```

(don't forget the period at the end, it will use the `Dockerfile` from the current location). Here
`mydhaccount` is the name of your `dockerhub` account. If you don't have a dockerhub account you can
build the image locally only (name the container whatever you like in that case, like just
`mygame`).

Docker images are stored centrally on your computer. You can see which ones you have available
locally with `docker images`. Once built, you have a couple of options to run your game.

### Run container from your game image for development

To run the container based on your game image locally for development, mount the local game
directory as before:

```
docker run -it --rm -p 4000:4000 -p 4001:4001 -p 4002:4002 -v $PWD:/usr/src/game --user $UID:$GID
mydhaccount/mygame
```

Evennia will start and you'll get output in the terminal, perfect for development. You should be
able to connect to the game with your clients normally.

### Deploy game image for production

Each time you rebuild the docker image as per the above instructions, the latest copy of your game
directory is actually copied inside the image (at `/usr/src/game/`). If you don't mount your on-disk
folder there, the internal one will be used. So for deploying evennia on a server, omit the `-v`
option and just give the following command:

```
docker run -it --rm -d -p 4000:4000 -p 4001:4001 -p 4002:4002 --user $UID:$GID mydhaccount/mygame
```

Your game will be downloaded from your docker-hub account and a new container will be built using
the image and started on the server! If your server environment forces you to use different ports,
you can just map the normal ports differently in the command above.

Above we added the `-d` option, which starts the container in *daemon* mode - you won't see any
return in the console. You can see it running with `docker ps`:

```bash
$ docker ps

CONTAINER ID     IMAGE       COMMAND                  CREATED              ...
f6d4ca9b2b22     mygame      "/bin/sh -c 'evenn..."   About a minute ago   ...
```

Note the container ID, this is how you manage the container as it runs.

```
   docker logs f6d4ca9b2b22      
```
Looks at the STDOUT output of the container (i.e. the normal server log)
```
   docker logs -f f6d4ca9b2b22   
```
Tail the log (so it updates to your screen 'live').
```
   docker pause f6d4ca9b2b22     
```
Suspend the state of the container. 
```
   docker unpause f6d4ca9b2b22   
```
Un-suspend it again after a pause. It will pick up exactly where it were.
```
   docker stop f6d4ca9b2b22      
```
Stop the container. To get it up again you need to use `docker run`, specifying ports etc. A new
container will get a new container id to reference.

## How it Works

The `evennia/evennia` docker image holds the evennia library and all of its dependencies. It also
has an `ONBUILD` directive which is triggered during builds of images derived from it. This
`ONBUILD` directive handles setting up a volume and copying your game directory code into the proper
location within the container.

In most cases, the Dockerfile for an Evennia-based game will only need the `FROM
evennia/evennia:latest` directive, and optionally a `MAINTAINER` directive if you plan to publish
your image on Docker Hub and would like to provide contact info.

For more information on Dockerfile directives, see the [Dockerfile
Reference](https://docs.docker.com/engine/reference/builder/).

For more information on volumes and Docker containers, see the Docker site's [Manage data in
containers](https://docs.docker.com/engine/tutorials/dockervolumes/) page.

### What if I Don't Want "LATEST"?

A new `evennia/evennia` image is built automatically whenever there is a new commit to the `master`
branch of Evennia. It is possible to create your own custom evennia base docker image based on any
arbitrary commit.

1. Use git tools to checkout the commit that you want to base your image upon. (In the example
below, we're checking out commit a8oc3d5b.)
```
git checkout -b my-stable-branch a8oc3d5b 
```
2. Change your working directory to the `evennia` directory containing `Dockerfile`. Note that
`Dockerfile` has changed over time, so if you are going far back in the commit history you might
want to bring a copy of the latest `Dockerfile` with you and use that instead of whatever version
was used at the time.
3. Use the `docker build` command to build the image based off of the currently checked out commit.
The example below assumes your docker account is **mydhaccount**.
```
docker build -t mydhaccount/evennia .
```
4. Now you have a base evennia docker image built off of a specific commit. To use this image to
build your game, you would modify **FROM** directive in the **Dockerfile** for your game directory
to be:

```
FROM mydhacct/evennia:latest
``` 

Note: From this point, you can also use the `docker tag` command to set a specific tag on your image
and/or upload it into Docker Hub under your account.

5. At this point, build your game using the same `docker build` command as usual. Change your
working directory to be your game directory and run

```
docker build -t mydhaccountt/mygame .
```

## Additional Creature Comforts

The Docker ecosystem includes a tool called `docker-compose`, which can orchestrate complex multi-
container applications, or in our case, store the default port and terminal parameters that we want
specified every time we run our container. A sample `docker-compose.yml` file to run a containerized
Evennia game in development might look like this:
```
version: '2'

services:
  evennia:
    image: mydhacct/mygame
    stdin_open: true
    tty: true
    ports:
      - "4001-4002:4001-4002"
      - "4000:4000"
    volumes: 
      - .:/usr/src/game
```
With this file in the game directory next to the `Dockerfile`, starting the container is as simple
as
```
docker-compose up
```
For more information about `docker-compose`, see [Getting Started with docker-
compose](https://docs.docker.com/compose/gettingstarted/).

> Note that with this setup you lose the `--user $UID` option. The problem is that the variable
`UID` is not available inside the configuration file `docker-compose.yml`. A workaround is to
hardcode your user and group id. In a terminal run `echo  $UID:$GID` and if for example you get
`1000:1000` you can add to `docker-compose.yml` a line `user: 1000:1000` just below the `image: ...`
line.