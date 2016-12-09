#/bin/bash
#------------------------------------------------------------
#
# GNU Screen bash startup script (Linux only)
#
# This script is meant for auto-restarting Evennia on a Linux server
# with the standard GNU Screen program installed. Evennia will be
# launched inside a detached Screen session, you can then connect
# to with screen -r <gamename>. This will make sure that the
# runner reload process is not killed when logging out of the server.
# A Screen session also has the advantage that one can connect to it
# and operate normally on the server after the fact.
#
# Usage:
#
# 1. First make sure Evennia can be started manually.
# 2. Copy this script to mygame/server.
# 3. Edit the GAMENAME, VIRTUALENV and GAMEDIR vars below to
#    match your game.
# 4. Make it executable with 'chmod u+x evennia-screen.sh'.
#
# See also evennia-screen-initd.sh for auto-starting evennia
# on the server.
#
#------------------------------------------------------------

# CHANGE to fit your game (obs: no spaces around the '=')

GAMENAME="mygame"
VIRTUALENV="/home/muddev/mud/pyenv"
GAMEDIR="/home/muddev/mud/mygame"

#------------------------------------------------------------

case $1 in
    start)
        if [ -z "$STY" ]; then
            if screen -S "$GAMENAME" -X select .>/dev/null; then
                # Session already exists. Send the start command instead.
                echo "(Re-)Starting Evennia."
                cd "$GAMEDIR"
                touch "$GAMEDIR"/server/logs/server.log
                screen -S $GAMENAME -p evennia -X stuff 'evennia --log start\n'
            else
                # start GNU Screen then run it with this same script, making sure to
                # not start Screen on the second call
                echo "Starting Evennia."
                exec screen -d -m -S "$GAMENAME" -t evennia /bin/bash "$0" "$1"
            fi
        else
            # this is executed inside the GNU Screen session
            source "$VIRTUALENV"/bin/activate
            cd "$GAMEDIR"
            # these will fail unless server died uncleanly
            rm "$GAMEDIR"/server/server.pid
            rm "$GAMEDIR"/server/portal.pid
            # make sure it exists for the first startup
            touch "$GAMEDIR"/server/logs/server.log
            # start evennia itself
            evennia --log start
            # we must run this to avoid the screen session exiting immediately
            exec sh
        fi
    ;;
    stop)
        cd "$GAMEDIR"
        screen -S "$GAMENAME" -p evennia -X stuff 'evennia stop\n'
        echo "Stopped Evennia."
    ;;
    reload | restart)
        cd "$GAMEDIR"
        screen -S "$GAMENAME" -p evennia -X stuff 'evennia --log reload\n'
        echo "Reloading Evennia."
    ;;
    *)
        echo "Usage: evennia-screen.sh {start|stop|restart|reload}"
    exit 1
;;

esac
