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

import time, random
from argparse import ArgumentParser
from twisted.conch import telnet
from twisted.internet import reactor, protocol
from twisted.internet.task import LoopingCall

from django.conf import settings
from evennia.utils import mod_import

# Load the dummyrunner settings module

DUMMYRUNNER_SETTINGS = mod_import(settings.DUMMYRUNNER_SETTINGS_MODULE)
DATESTRING = "%Y%m%d%H%M%S"

# Settings

# number of clients to launch if no input is given on command line
NCLIENTS = 1
# time between each 'tick', in seconds, if not set on command
# line. All launched clients will be called upon to possibly do an
# action with this frequency.
TIMESTEP = DUMMYRUNNER_SETTINGS.TIMESTEP
# chance of a client performing an action, per timestep. This helps to
# spread out usage randomly, like it would be in reality.
CHANCE_OF_ACTION = DUMMYRUNNER_SETTINGS.CHANCE_OF_ACTION
# spread out the login action separately, having many players create accounts
# and connect simultaneously is generally unlikely.
CHANCE_OF_LOGIN = DUMMYRUNNER_SETTINGS.CHANCE_OF_LOGIN
# Port to use, if not specified on command line
TELNET_PORT = DUMMYRUNNER_SETTINGS.TELNET_PORT or settings.TELNET_PORTS[0]
#
NLOGGED_IN = 0

# Messages

INFO_STARTING = \
    """
    Dummyrunner starting, {N} dummy player(s).

    Use Ctrl-C to stop/disconnect clients.
    """

ERROR_FEW_ACTIONS = \
"""
Dummyrunner error: The ACTIONS tuple is too short: it must contain at
least login- and logout functions.
"""


HELPTEXT = """
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

        You can also customize the dummyrunner by modifying
        a setting file specified by DUMMYRUNNER_SETTINGS_MODULE

  3) Start Evennia like normal, optionally with profiling (--profile)
  4) run this dummy runner via the evennia launcher:

        evennia --dummyrunner <nr_of_clients>

  5) Log on and determine if game remains responsive despite the
     heavier load. Note that if you do profiling, there is an
     additional overhead from the profiler too!
  6) If you use profiling, let the game run long enough to gather
     data, then stop the server, ideally from inside it with
     @shutdown. You can inspect the server.prof file from a python
     prompt (see Python's manual on cProfiler).

"""

#------------------------------------------------------------
# Helper functions
#------------------------------------------------------------


ICOUNT = 0
def idcounter():
    "makes unique ids"
    global ICOUNT
    ICOUNT += 1
    return str(ICOUNT)


GCOUNT = 0
def gidcounter():
    "makes globally unique ids"
    global GCOUNT
    GCOUNT += 1
    return "%s-%s" % (time.strftime(DATESTRING), ICOUNT)


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
        self.cid = idcounter()
        self.key = "Dummy-%s" % self.cid
        self.gid = "%s-%s" % (time.strftime(DATESTRING), self.cid)
        self.istep = 0
        self.loggedin = False
        self.exits = [] # exit names created
        self.objs = [] # obj names created

        self._report = ""
        self._cmdlist = [] # already stepping in a cmd definition
        nactions = len(self.factory.actions) # this has already been normalized
        if nactions < 2:
            raise RuntimeError(ERROR_FEW_ACTIONS)
        self._login = self.factory.actions[0]
        self._logout = self.factory.actions[1]
        self._actions = self.factory.actions[2:]

        reactor.addSystemEventTrigger('before', 'shutdown', self.logout)

        # start client tick
        d = LoopingCall(self.step)
        # dissipate exact step by up to +/- 0.5 second
        timestep = TIMESTEP + (-0.5 + (random.random()*1.0))
        d.start(timestep, now=True).addErrback(self.error)


    def dataReceived(self, data):
        "Echo incoming data to stdout"
        pass

    def connectionLost(self, reason):
        "loosing the connection"

    def error(self, err):
        "error callback"
        print err

    def counter(self):
        "produces a unique id, also between clients"
        return gidcounter()

    def logout(self):
        "Causes the client to log out of the server. Triggered by ctrl-c signal."
        cmd = self._logout(self)
        print "client %s(%s) logout (%s actions)" % (self.key, self.cid, self.istep)
        self.sendLine(cmd)

    def step(self):
        """
        Perform a step. This is called repeatedly by the runner
        and causes the client to issue commands to the server.
        This holds all "intelligence" of the dummy client.
        """
        global NLOGGED_IN

        rand = random.random()

        if not self._cmdlist:
            # no commands ready. Load some.

            if not self.loggedin:
                if rand < CHANCE_OF_LOGIN:
                    # get the login commands
                    self._cmdlist = list(makeiter(self._login(self)))
                    NLOGGED_IN += 1 # this is for book-keeping
                    print "connecting client %s (%i/%i)..." % (self.key, NLOGGED_IN, NCLIENTS)
                    self.loggedin = True
            else:
                # we always pick a cumulatively random function
                crand = random.random()
                cfunc = [func for cprob, func in self._actions if cprob >= crand][0]
                self._cmdlist = list(makeiter(cfunc(self)))

        # at this point we always have a list of commands
        if rand < CHANCE_OF_ACTION:
            # send to the game
            self.sendLine(str(self._cmdlist.pop(0)))
            self.istep += 1


class DummyFactory(protocol.ClientFactory):
    protocol = DummyClient
    def __init__(self, actions):
        "Setup the factory base (shared by all clients)"
        self.actions = actions

#------------------------------------------------------------
# Access method:
# Starts clients and connects them to a running server.
#------------------------------------------------------------

def start_all_dummy_clients(nclients):

    global NCLIENTS
    NCLIENTS = int(nclients)
    actions = DUMMYRUNNER_SETTINGS.ACTIONS

    # make sure the probabilities add up to 1
    pratio = 1.0 / sum(tup[0] for tup in actions[2:])
    flogin, flogout, probs, cfuncs = actions[0], actions[1], [tup[0] * pratio for tup in actions[2:]], [tup[1] for tup in actions[2:]]
    # create cumulative probabilies for the random actions
    cprobs = [sum(v for i,v in enumerate(probs) if i<=k) for k in range(len(probs))]
    # rebuild a new, optimized action structure
    actions = (flogin, flogout, zip(cprobs, cfuncs))

    # setting up all clients (they are automatically started)
    factory = DummyFactory(actions)
    for i in range(NCLIENTS):
        reactor.connectTCP("localhost", TELNET_PORT, factory)
    # start reactor
    reactor.run()

#------------------------------------------------------------
# Command line interface
#------------------------------------------------------------

if __name__ == '__main__':

    # parsing command line with default vals
    parser = ArgumentParser(description=HELPTEXT)
    parser.add_argument("-N", nargs=1, default=1, dest="nclients",
                        help="Number of clients to start")

    args = parser.parse_args()

    print INFO_STARTING.format(N=args.nclients[0])
    t0 = time.time()
    start_all_dummy_clients(nclients=args.nclients[0])
    ttot = time.time() - t0
    print "... dummy client runner stopped after %i seconds." % ttot
