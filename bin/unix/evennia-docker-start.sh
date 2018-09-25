#! /bin/bash

# called by the Dockerfile to start the server in docker mode

# remove leftover .pid files (such as from when dropping the container)
rm /usr/src/game/server/*.pid >& /dev/null || true

# start evennia server; log to server.log but also output to stdout so it can 
# be viewed with docker-compose logs
exec 3>&1; evennia start -l
