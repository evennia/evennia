#####
# Base docker image for running Evennia-based games in a container.
#
# Install:
#   install `docker` (http://docker.com)
#
# Usage:
#    cd to a folder where you want your game data to be (or where it already is).
#
#        docker run -it --rm -p 4000:4000 -p 4001:4001 -p 4002:4002 -v $PWD:/usr/src/game evennia/evennia
#
#    (If your OS does not support $PWD, replace it with the full path to your current
#    folder).
#
#    You will end up in a shell where the `evennia` command is available. From here you
#    can initialize and/or run the game normally. Use Ctrl-D to exit the evennia docker container.
#    For more info see: https://github.com/evennia/evennia/wiki/Getting-Started#quick-start
#
#    You can also start evennia directly by passing arguments to the folder:
#
#        docker run -it --rm -p 4000:4000 -p 4001:4001 -p 4002:4002 -v $PWD:/usr/src/game evennia/evennia evennia start -l
#
#    This will start Evennia running as the core process of the container. Note that you *must* use -l
#    or one of the foreground modes (like evennia ipstart), since otherwise the container will immediately
#    die because of having no foreground process.
#
# The evennia/evennia base image is found on DockerHub and can also be used
# as a base for creating your own custom containerized Evennia game. For more
# info, see https://github.com/evennia/evennia/wiki/Running%20Evennia%20in%20Docker .
#
FROM python:3.7-alpine

LABEL maintainer="www.evennia.com"

# install compilation environment
RUN apk update && apk add bash gcc jpeg-dev musl-dev procps \
libffi-dev openssl-dev zlib-dev gettext

# add the files required for pip installation
COPY ./setup.py /usr/src/evennia/
COPY ./requirements.txt /usr/src/evennia/
COPY ./evennia/VERSION.txt /usr/src/evennia/evennia/
COPY ./bin /usr/src/evennia/bin/

# install dependencies
RUN pip install --upgrade pip && pip install -e /usr/src/evennia --trusted-host pypi.python.org
RUN pip install cryptography pyasn1 service_identity

# add the project source; this should always be done after all
# expensive operations have completed to avoid prematurely
# invalidating the build cache.
COPY . /usr/src/evennia

# add the game source when rebuilding a new docker image from inside
# a game dir
ONBUILD COPY . /usr/src/game

# make the game source hierarchy persistent with a named volume.
# mount on-disk game location here when using the container
# to just get an evennia environment.
VOLUME /usr/src/game

# set the working directory
WORKDIR /usr/src/game

# set bash prompt
ENV PS1 "evennia|docker \w $ "

# create and switch to a non-root user for runtime security
# -D - do not set a password
# -H - do not create a home directory
# -s /bin/false - set login shell to /bin/false
RUN adduser -D -H -s /bin/false evennia
USER evennia

# startup a shell when we start the container
ENTRYPOINT ["/usr/src/evennia/bin/unix/evennia-docker-start.sh"]

# expose the telnet, webserver and websocket client ports
EXPOSE 4000 4001 4002
