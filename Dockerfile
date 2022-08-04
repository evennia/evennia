# syntax = docker/dockerfile:1.3
#####
# Base docker image for running Evennia-based games in a container.
#
# Install:
#   install `docker` (https://docker.com)
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
# info, see https://evennia.com/docs/latest/Setup/Installation-Docker
#
ARG BASE_IMAGE=python
ARG BASE_VERSION=3.10
ARG BASE_IMAGE_TAG=$BASE_VERSION-slim

FROM $BASE_IMAGE:$BASE_IMAGE_TAG as builder

LABEL maintainer="www.evennia.com"

# install needed packages. We don't want to clean apt
# at the end as we will use this stage as a cache
RUN rm /etc/apt/apt.conf.d/docker-clean\
    && apt-get update \
    && apt-get install -y \
        bash \
        build-essential \
        gettext \
        libffi-dev \
        libjpeg-dev \
        libssl-dev \
        procps \
        zlib1g-dev

# add the files required for pip installation
COPY setup.py requirements.txt /usr/src/evennia/
COPY evennia/VERSION.txt /usr/src/evennia/evennia/
COPY bin /usr/src/evennia/bin/

# install dependencies
WORKDIR /srv/cache
# we only warm up pip caches by using wheel
RUN pip install --upgrade pip \
    && pip wheel -e /usr/src/evennia --trusted-host pypi.python.org \
    && pip wheel \
        cryptography \
        pyasn1 \
        service_identity

FROM $BASE_IMAGE:$BASE_IMAGE_TAG as deps

LABEL maintainer="www.evennia.com"

# create a non-root user for runtime security
RUN adduser evennia \
        --disabled-password \
        --no-create-home \
        --shell /bin/false \
        --gecos ''

# only copy things needed to pip install, so to not invalidate docker caches
COPY --from=builder /usr/src/evennia /usr/src/evennia

# move to the wheel cache dir we warmed during "builder" stage
WORKDIR /srv/cache
# here we install everything staying offline, ie. we know we only
# install what we've prepared before. This can be tested and used
# in the following stages
RUN \
    --mount=type=bind,target=/root/.cache/pip,from=builder,source=/root/.cache/pip \
    --mount=type=bind,target=/srv,from=builder,source=/srv \
    --mount=type=bind,target=/var/cache/apt,from=builder,source=/var/cache/apt,rw \
    --mount=type=bind,target=/var/lib/apt/lists,from=builder,source=/var/lib/apt/lists \
    --network=none \
    set -x; \
    pip install \
        -f . \
        --no-index \
        -e /usr/src/evennia \
    && pip install \
        -f . \
        --no-index \
        cryptography \
        pyasn1 \
        service_identity \
    && apt-get install -y \
        gettext \
        libjpeg62-turbo \
        procps

COPY . /usr/src/evennia


FROM deps as test

# you can also use "auto" (w/o quotes) for using as much as available cores
ARG PARALLEL=4

LABEL maintainer="www.evennia.com"

RUN set -x; \
    apt-get update \
    && apt-get install -y \
        gfortran \
        libblas-dev \
        liblapack-dev \
    && pip install -r /usr/src/evennia/requirements_extra.txt

USER evennia
WORKDIR /tmp

RUN evennia --init test \
    && cd test \
    && evennia migrate \
    && evennia test evennia --parallel $PARALLEL


FROM deps

LABEL maintainer="www.evennia.com"

# make the game source hierarchy persistent with a named volume.
# mount on-disk game location here when using the container
# to just get an evennia environment.
VOLUME /usr/src/game

# set bash prompt
ENV PS1 "evennia|docker \w $ "

# set the working directory
WORKDIR /usr/src/game

# add the game source when rebuilding a new docker image from inside
# a game dir
ONBUILD COPY . /usr/src/game

# switch to a non-root user for runtime security
USER evennia

# startup a shell when we start the container
ENTRYPOINT ["/usr/src/evennia/bin/unix/evennia-docker-start"]

# expose the telnet, webserver and websocket client ports
EXPOSE 4000 4001 4002
