"""
Dummy client runner

This module implements a stand-alone launcher for stress-testing
an Evennia game. It will launch any number of fake clients. These
clients will log into the server and start doing random operations.
Customizing and weighing these operations differently depends on
which type of game is tested. The module contains a testing module
for plain Evennia.

Please note that you shouldn't run this on a production server!
Launch the program without any arguments or options to see a
full step-by-step setup help.

Basically (for testing default Evennia):

 - Use an empty/testing database.
 - set PERMISSION_PLAYER_DEFAULT = "Builders"
 - start server, eventually with profiling active
 - launch this client runner

If you want to customize the runner's client actions
(because you changed the cmdset or needs to better
match your use cases or add more actions), you can
change which actions by adding a path to

   DUMMYRUNNER_ACTIONS_MODULE = <path.to.your.module>

in your settings. See utils.dummyrunner_actions.py
for instructions on how to define this module.

"""

import os, sys, time, random
from optparse import OptionParser
from twisted.conch import telnet
from twisted.internet import reactor, protocol
# from twisted.application import internet, service
# from twisted.web import client
from twisted.internet.task import LoopingCall

# Tack on the root evennia directory to the python path and initialize django settings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from django.core.management import setup_environ
from game import settings
setup_environ(settings)

from django.conf import settings
from src.utils import utils

HELPTEXT = """

Usage: dummyrunner.py [-h][-v][-V] [nclients]

DO NOT RUN THIS ON A PRODUCTION SERVER! USE A CLEAN/TESTING DATABASE!

This stand-alone program launches dummy telnet clients against a
running Evennia server. The idea is to mimic real players logging in
and repeatedly doing resource-heavy commands so as to stress test the
game. It uses the default command set to log in and issue commands, so
if that was customized, some of the functionality will not be tested
(it will not fail, the commands will just not be recognized).  The
running clients will create new objects and rooms all over the place
as part of their running, so using a clean/testing database is
strongly recommended.

Setup:
  1) setup a fresh/clean database (if using sqlite, just safe-copy
     away your real evennia.db3 file and create a new one with
     manage.py)
  2) in game/settings.py, add

        PERMISSION_PLAYER_DEFAULT="Builders"

  3a) Start Evennia like normal.
  3b) If you want profiling, start Evennia like this instead:

        python runner.py -S start

     this will start Evennia under cProfiler with output server.prof.
  4) run this dummy runner:

        python dummyclients.py <nr_of_clients> [timestep] [port]

     Default is to connect one client to port 4000, using a 5 second
     timestep.  Increase the number of clients and shorten the
     timestep (minimum is 1s) to further stress the game.

     You can stop the dummy runner with Ctrl-C.

  5) Log on and determine if game remains responsive despite the
     heavier load. Note that if you do profiling, there is an
     additional overhead from the profiler too!
  6) If you use profiling, let the game run long enough to gather
     data, then stop the server. You can inspect the server.prof file
     from a python prompt (see Python's manual on cProfiler).

"""
# number of clients to launch if no input is given on command line
DEFAULT_NCLIENTS = 1
# time between each 'tick', in seconds, if not set on command
# line. All launched clients will be called upon to possibly do an
# action with this frequency.
DEFAULT_TIMESTEP = 2
# Port to use, if not specified on command line
DEFAULT_PORT = settings.TELNET_PORTS[0]
# chance of an action happening, per timestep. This helps to
# spread out usage randomly, like it would be in reality.
CHANCE_OF_ACTION = 0.1


#------------------------------------------------------------
# Helper functions
#------------------------------------------------------------

def idcounter():
    "generates subsequent id numbers"
    idcount = 0
    while True:
        idcount += 1
        yield idcount
OID = idcounter()
CID = idcounter()

def makeiter(obj):
    "makes everything iterable"
    if not hasattr(obj, '__iter__'):
        return [obj]
    return obj

#------------------------------------------------------------
# Client classes
#------------------------------------------------------------

class DummyClient(telnet.StatefulTelnetProtocol):
    """
    Handles connection to a running Evennia server,
    mimicking a real player by sending commands on
    a timer.
    """

    def connectionMade(self):

        # public properties
        self.cid = CID.next()
        self.istep = 0
        self.exits = [] # exit names created
        self.objs = [] # obj names created

        self._report = ""
        self._cmdlist = [] # already stepping in a cmd definition
        self._ncmds = 0
        self._actions = self.factory.actions
        self._echo_brief = self.factory.verbose == 1
        self._echo_all = self.factory.verbose == 2
        #print " ** client %i connected." % self.cid

        reactor.addSystemEventTrigger('before', 'shutdown', self.logout)

        # start client tick
        d = LoopingCall(self.step)
        d.start(self.factory.timestep, now=True).addErrback(self.error)

    def dataReceived(self, data):
        "Echo incoming data to stdout"
        if self._echo_all:
            print data

    def connectionLost(self, reason):
        "loosing the connection"
        #print " ** client %i lost connection." % self.cid

    def error(self, err):
        "error callback"
        print err

    def counter(self):
        "produces a unique id, also between clients"
        return OID.next()

    def logout(self):
        "Causes the client to log out of the server. Triggered by ctrl-c signal."
        cmd, report = self._actions[1](self)
        print "client %i %s (%s actions)" % (self.cid, report, self.istep)
        self.sendLine(cmd)

    def step(self):
        """
        Perform a step. This is called repeatedly by the runner
        and causes the client to issue commands to the server.
        This holds all "intelligence" of the dummy client.
        """
        if random.random() > CHANCE_OF_ACTION:
            return
        if not self._cmdlist:
            # no cmdlist in store, get a new one
            if self.istep == 0:
                cfunc = self._actions[0]
            else: # random selection using cumulative probabilities
                rand = random.random()
                cfunc = [func for cprob, func in self._actions[2] if cprob >= rand][0]
            # assign to internal cmdlist
            cmd, self._report = cfunc(self)
            self._cmdlist = list(makeiter(cmd))
            self._ncmds = len(self._cmdlist)
        # output
        if self.istep == 0 and not (self._echo_brief or self._echo_all):
            print "client %i %s" % (self.cid, self._report)
        elif self.istep == 0 or self._echo_brief or self._echo_all:
            print "client %i %s (%i/%i)" % (self.cid, self._report, self._ncmds-(len(self._cmdlist)-1), self._ncmds)
        # launch the action by popping the first element from cmdlist (don't hide tracebacks)
        self.sendLine(str(self._cmdlist.pop(0)))
        self.istep += 1 # only steps up if an action is taken

class DummyFactory(protocol.ClientFactory):
    protocol = DummyClient
    def __init__(self, actions, timestep, verbose):
        "Setup the factory base (shared by all clients)"
        self.actions = actions
        self.timestep = timestep
        self.verbose = verbose

#------------------------------------------------------------
# Access method:
# Starts clients and connects them to a running server.
#------------------------------------------------------------

def start_all_dummy_clients(actions, nclients=1, timestep=5, telnet_port=4000, verbose=0):

    # validating and preparing the action tuple

    # make sure the probabilities add up to 1
    pratio = 1.0 / sum(tup[0] for tup in actions[2:])
    flogin, flogout, probs, cfuncs = actions[0], actions[1], [tup[0] * pratio for tup in actions[2:]], [tup[1] for tup in actions[2:]]
    # create cumulative probabilies for the random actions
    cprobs = [sum(v for i,v in enumerate(probs) if i<=k) for k in range(len(probs))]
    # rebuild a new, optimized action structure
    actions = (flogin, flogout, zip(cprobs, cfuncs))

    # setting up all clients (they are automatically started)
    factory = DummyFactory(actions, timestep, verbose)
    for i in range(nclients):
        reactor.connectTCP("localhost", telnet_port, factory)
    # start reactor
    reactor.run()

#------------------------------------------------------------
# Command line interface
#------------------------------------------------------------

if __name__ == '__main__':

    # parsing command line with default vals
    parser = OptionParser(usage="%prog [options] <nclients> [timestep, [port]]",
                          description="This program requires some preparations to run properly. Start it without any arguments or options for full help.")
    parser.add_option('-v', '--verbose', action='store_const', const=1, dest='verbose',
                      default=0,help="echo brief description of what clients do every timestep.")
    parser.add_option('-V', '--very-verbose', action='store_const',const=2, dest='verbose',
                      default=0,help="echo all client returns to stdout (hint: use only with nclients=1!)")

    options, args = parser.parse_args()

    nargs = len(args)
    nclients = DEFAULT_NCLIENTS
    timestep = DEFAULT_TIMESTEP
    port = DEFAULT_PORT
    try:
        if not args : raise Exception
        if nargs > 0: nclients = max(1, int(args[0]))
        if nargs > 1: timestep = max(1, int(args[1]))
        if nargs > 2: port = int(args[2])
    except Exception:
        print HELPTEXT
        sys.exit()

    # import the ACTION tuple from a given module
    try:
        action_modpath = settings.DUMMYRUNNER_ACTIONS_MODULE
    except AttributeError:
        # use default
        action_modpath = "src.utils.dummyrunner.dummyrunner_actions"
    actions = utils.variable_from_module(action_modpath, "ACTIONS")

    print "Connecting %i dummy client(s) to port %i using a %i second timestep ... " % (nclients, port, timestep)
    t0 = time.time()
    start_all_dummy_clients(actions, nclients, timestep, port,
                       verbose=options.verbose)
    ttot = time.time() - t0
    print "... dummy client runner finished after %i seconds." % ttot
