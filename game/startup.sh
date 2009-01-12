#!/bin/bash
#############################################################################
# LINUX/UNIX SERVER STARTUP SCRIPT
# Sets the appropriate environmental variables and launches the server
# process. Run without flags for daemon mode.
# It can be used for stoping the server.
#
# FLAGS
# -i    Interactive mode
# -d    Daemon mode
# -s    Stop the running server
# -h	Show help display
#############################################################################

init () {
	## Sets environmental variables and preps the logs.
	export PYTHONPATH="..":$PYTHONPATH
	export DJANGO_SETTINGS_MODULE="game.settings"
	mv -f logs/evennia.log logs/evennia.logs.old
}

startup_interactive() {
	## Starts the server in interactive mode.
	init
	echo "Starting in interactive mode..."
	twistd -n --python=../src/server.py
}

startup_daemon() {
	## Starts the server in daemon mode.
	init
	twistd --logfile=logs/evennia.log --python=../src/server.py
}

stop_server() {
	## Stops the running server
        echo "Stopping the server..."
	kill `cat twistd.pid`
}

help_display() {
	echo "SERVER STARTUP SCRIPT"
	echo "Sets the appropriate environmental variables and launches the server"
	echo "process. Run without flags for daemon mode."
	echo ""
	echo "FLAGS"
	echo " -i    Interactive mode"
	echo " -d    Daemon mode"
	echo " -s    Stop the running server"
	echo " -h    Show help display"

}

case "$1" in 
	'-i') 
		startup_interactive
	;;
	'-d')
		startup_daemon
	;;
	'-s')
		stop_server
	;;
	'--help')
		help_display
	;;
	'-h')
		help_display
	;;
	*)
		# If no argument is provided, start in daemon mode.
		startup_daemon
esac
