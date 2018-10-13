#! /bin/sh

# called by the Dockerfile to start the server in docker mode

# remove leftover .pid files (such as from when dropping the container)
rm /usr/src/game/server/*.pid >& /dev/null || true

PS1="evennia|docker \w $ "

cmd="$@"
output="Docker starting with argument '$cmd' ..."
if test -z $cmd; then
    cmd="bash"
    output="No argument given, starting shell ..."
fi

echo $output
exec 3>&1; $cmd
