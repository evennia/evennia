#####
# Base docker image for running Evennia-based games in a container.
#
# This Dockerfile creates the evennia/evennia docker image
# on DockerHub, which can be used as the basis for creating
# an Evennia game within a container. This base image can be
# found in DockerHub at https://hub.docker.com/r/evennia/evennia/
#
# For more information on using it to build a container to run your game, see
#
# https://github.com/evennia/evennia/wiki/Running%20Evennia%20in%20Docker
#
FROM alpine

# install compilation environment
RUN apk update && apk add python py-pip python-dev py-setuptools gcc musl-dev jpeg-dev zlib-dev

# add the project source
ADD . /usr/src/evennia

# install dependencies
RUN pip install -e /usr/src/evennia --index-url=http://pypi.python.org/simple/ --trusted-host pypi.python.org

# add the game source during game builds
ONBUILD ADD . /usr/src/game

# make the game source hierarchy persistent with a named volume.
# during development this is typically superceded by directives in
# docker-compose.yml or the CLI to mount a local directory.
VOLUME /usr/src/game

# set the working directory
WORKDIR /usr/src

# init evennia
RUN evennia --init mygame

WORKDIR /usr/src/mygame
RUN evennia migrate

# startup command
# ENTRYPOINT  ["evennia",  "start"]

# expose the telnet, webserver and websocket client ports
EXPOSE 4000 4001 4005
