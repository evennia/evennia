#!/bin/bash 
#
# Evennia init.d Screen launcher script (Linux)
#
# This requires a Linux using init.d. I is used togeter
# with the evennia-screen.sh script, which must be working
# before setting this one up. This script is meant to be
# used as part of Linux' automatic services and requires
# root to set up.
#
# Usage:
#  1. sudo cp evennia-screen-initd.sh /etc/init.d/evennia
#  2. cd /etc/init.d
#  3. Edit this script (now renamed to 'evennia') and
#     change SCRIPTPATH and USER below to fit your setup.
#  4. sudo chown root:root evennia
#  5. sudo chmod 755 evennia
#
# You can now use (as root) ´services evennia start|stop|reload`
# to operate the server. The server will run as the USER you
# specify and must thus have access to start the server 
# (*don't* set it to run as root!).
#
# To make Evennia auto-start when the server reboots, run
# the following:
#
#    sudo update-rc.d evennia defaults 91
#


# CHANGE to fit your setup (obs: no spaces around the '=')

SCRIPTPATH="/home/muddev/mud/mygame/server/evennia-screen.sh"
USER="muddev"

#------------------------------------------------------------
case $1 in 
    start | stop | reload | restart)
        # run the start script and forward the argument to it
        su - "$USER" -c "$SCRIPTPATH $1"
    ;;
    *)
       echo "Usage: evennia {start|stop|restart|reload}"
       exit 1
    ;;
esac
exit 0
