#!/usr/bin/env python
import getopt # for parsing command line arguments
import os # for OS related fonctions 
import sys # for getting command line arguments

def init():
	"""main fonction for configuring tne system for start-up"""
	print 'Configuring evirontment variables'
	os.putenv('PYTHONPATH','..')
	os.putenv('DJANGO_SETTINGS_MODULE','game.settings')
	print 'Renaming old logs as .old'
	os.rename('logs/evennia.log','logs/evennia.log.old')
	# no error checking for rename for now

def start_daemon():
	"""start the server in daemon mode by using os.sysytem to run twistd""" 
	print 'Starting in Daemon Modea'
	os.system('twistd --logfile=logs/evennia.log --python=../src/server.py')

def start_interactive():
	"""start in inretactive mode by using os.sysytem to run twistd. this is default for windows for now"""
	print 'Starting in Interactive Mode'
	os.system('twistd --logfile=logs/evennia.log --python=../src/server.py')

def stop_server():
	"""kill the running server this fonction is unix only,
	windows impletation will come with subprocess module for everything."""
	if os.name == 'posix': 
		print 'Stoping The Server'
		os.system('kill `cat twistd.pid`')
	elif os.name == 'nt':
		print 'TODO not implented'
	else:
		print 'Unknown OS delected, can not kill'
def usage():
	print 'Sets the appropriate environmental variables and launches the server\nprocess. Run without flags for daemon mode.\n\nFLAGS\n  -i    Interactive mode\n  -d    Daemon mode\n  -s    Stop the running server\n  -h    Show help display\n, No Default Behavour Exits',


def main(argv):
	""" main program body """
	try:
		opts, args = getopt.getopt(argv, "hids",[help])
	except getopt.getopterror:
		usage()
		sys.exit(2)
	
	for opt, arg in opts:
		if opt in ("-h","--help"):
			usage()
			sys.exit()
		elif opt == '-i':
			start_interactive()
		elif opt == '-d':
			start_daemon()
		elif opt == '-s':
			stop_server()
		else:
			usage()
	
			
if __name__ == '__main__':
	main(sys.argv[1:])
