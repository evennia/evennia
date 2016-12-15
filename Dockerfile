FROM python:2.7-alpine
MAINTAINER Dan Feeney "feend78@gmail.com"

# install compilation environment
RUN apk update && apk add gcc musl-dev

# add the project source
ADD . /usr/src/evennia

# install dependencies
RUN pip install -e /usr/src/evennia

# add the game source during game builds
ONBUILD ADD . /usr/src/game

# make the game source hierarchy persistent with a named volume.
# during development this is typically superceded by directives in 
# docker-compose.yml or the CLI to mount a local directory.
VOLUME /usr/src/game

# set the working directory
WORKDIR /usr/src/game

# startup command
CMD ["evennia", "-i", "start"]

# expose the default ports
EXPOSE 8000 8001 4000
