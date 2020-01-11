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
 - set PERMISSION_ACCOUNT_DEFAULT = "Builder"
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


import sys
import time
import random
from argparse import ArgumentParser
from twisted.conch import telnet
from twisted.internet import reactor, protocol
from twisted.internet.task import LoopingCall

from django.conf import settings
from evennia.utils import mod_import, time_format

# Load the dummyrunner settings module

DUMMYRUNNER_SETTINGS = mod_import(settings.DUMMYRUNNER_SETTINGS_MODULE)
if not DUMMYRUNNER_SETTINGS:
    raise IOError(
        "Error: Dummyrunner could not find settings file at %s"
        % settings.DUMMYRUNNER_SETTINGS_MODULE
    )

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
# spread out the login action separately, having many accounts create accounts
# and connect simultaneously is generally unlikely.
CHANCE_OF_LOGIN = DUMMYRUNNER_SETTINGS.CHANCE_OF_LOGIN
# Port to use, if not specified on command line
TELNET_PORT = DUMMYRUNNER_SETTINGS.TELNET_PORT or settings.TELNET_PORTS[0]
#
NLOGGED_IN = 0


# Messages


INFO_STARTING = """
    Dummyrunner starting using {N} dummy account(s). If you don't see
    any connection messages, make sure that the Evennia server is
    running.

    Use Ctrl-C to stop/disconnect clients.
    """

ERROR_NO_MIXIN = """
    Error: Evennia is not set up for dummyrunner. Before starting the
    server, make sure to include the following at *the end* of your
    settings file (remove when not using dummyrunner!):

        from evennia.server.profiling.settings_mixin import *

    This will change the settings in the following way:
        - change PERMISSION_ACCOUNT_DEFAULT to 'Developer' to allow clients
          to test all commands
        - change PASSWORD_HASHERS to use a faster (but less safe) algorithm
          when creating large numbers of accounts at the same time

    If you don't want to use the custom settings of the mixin for some
    reason, you can change their values manually after the import, or
    add DUMMYRUNNER_MIXIN=True to your settings file to avoid this
    error completely.

    Warning: Don't run dummyrunner on a production database! It will
    create a lot of spammy objects and accounts!
    """


ERROR_FEW_ACTIONS = """
    Dummyrunner settings error: The ACTIONS tuple is too short: it must
    contain at least login- and logout functions.
    """


HELPTEXT = """
DO NOT RUN THIS ON A PRODUCTION SERVER! USE A CLEAN/TESTING DATABASE!

This stand-alone program launches dummy telnet clients against a
running Evennia server. The idea is to mimic real accounts logging in
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
     `evennia migrate`)
  2) in server/conf/settings.py, add

        PERMISSION_ACCOUNT_DEFAULT="Builder"

     This is so that the dummy accounts can test building operations.
     You can also customize the dummyrunner by modifying a setting
     file specified by DUMMYRUNNER_SETTINGS_MODULE

  3) Start Evennia like normal, optionally with profiling (--profile)
  4) Run this dummy runner via the evennia launcher:

        evennia --dummyrunner <nr_of_clients>

  5) Log on and determine if game remains responsive despite the
     heavier load. Note that if you activated profiling, there is a
     considerate additional overhead from the profiler too so you
     should usually not consider game responsivity when using the
     profiler at the same time.
  6) If you use profiling, let the game run long enough to gather
     data, then stop the server cleanly using evennia stop or @shutdown.
     @shutdown. The profile appears as
     server/logs/server.prof/portal.prof (see Python's manual on
     cProfiler).

Notes:

The dummyrunner tends to create a lot of accounts all at once, which is
a very heavy operation. This is not a realistic use-case - what you want
to test is performance during run. A large
number of clients here may lock up the client until all have been
created. It may be better to connect multiple dummyrunners instead of
starting one single one with a lot of accounts. Exactly what this number
is depends on your computer power. So start with 10-20 clients and increase
until you see the initial login slows things too much.

"""

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------


ICOUNT = 0


def idcounter():
    """
    Makes unique ids.

    Returns:
        count (int): A globally unique counter.

    """
    global ICOUNT
    ICOUNT += 1
    return str(ICOUNT)


GCOUNT = 0


def gidcounter():
    """
    Makes globally unique ids.

    Returns:
        count (int); A globally unique counter.

    """
    global GCOUNT
    GCOUNT += 1
    return "%s-%s" % (time.strftime(DATESTRING), GCOUNT)


def makeiter(obj):
    """
    Makes everything iterable.

    Args:
        obj (any): Object to turn iterable.

    Returns:
        iterable (iterable): An iterable object.
    """
    return obj if hasattr(obj, "__iter__") else [obj]


# ------------------------------------------------------------
# Client classes
# ------------------------------------------------------------


class DummyClient(telnet.StatefulTelnetProtocol):
    """
    Handles connection to a running Evennia server,
    mimicking a real account by sending commands on
    a timer.

    """

    def connectionMade(self):
        """
        Called when connection is first established.

        """
        # public properties
        self.cid = idcounter()
        self.key = "Dummy-%s" % self.cid
        self.gid = "%s-%s" % (time.strftime(DATESTRING), self.cid)
        self.istep = 0
        self.exits = []  # exit names created
        self.objs = []  # obj names created

        self._connected = False
        self._loggedin = False
        self._logging_out = False
        self._report = ""
        self._cmdlist = []  # already stepping in a cmd definition
        self._login = self.factory.actions[0]
        self._logout = self.factory.actions[1]
        self._actions = self.factory.actions[2:]

        reactor.addSystemEventTrigger("before", "shutdown", self.logout)

    def dataReceived(self, data):
        """
        Called when data comes in over the protocol. We wait to start
        stepping until the server actually responds

        Args:
            data (str): Incoming data.

        """
        if not self._connected and not data.startswith(chr(255)):
            # wait until we actually get text back (not just telnet
            # negotiation)
            self._connected = True
            # start client tick
            d = LoopingCall(self.step)
            # dissipate exact step by up to +/- 0.5 second
            timestep = TIMESTEP + (-0.5 + (random.random() * 1.0))
            d.start(timestep, now=True).addErrback(self.error)

    def connectionLost(self, reason):
        """
        Called when loosing the connection.

        Args:
            reason (str): Reason for loosing connection.

        """
        if not self._logging_out:
            print("client %s(%s) lost connection (%s)" % (self.key, self.cid, reason))

    def error(self, err):
        """
        Error callback.

        Args:
            err (Failure): Error instance.
        """
        print(err)

    def counter(self):
        """
        Produces a unique id, also between clients.

        Returns:
            counter (int): A unique counter.

        """
        return gidcounter()

    def logout(self):
        """
        Causes the client to log out of the server. Triggered by ctrl-c signal.

        """
        self._logging_out = True
        cmd = self._logout(self)
        print("client %s(%s) logout (%s actions)" % (self.key, self.cid, self.istep))
        self.sendLine(cmd)

    def step(self):
        """
        Perform a step. This is called repeatedly by the runner and
        causes the client to issue commands to the server.  This holds
        all "intelligence" of the dummy client.

        """
        global NLOGGED_IN

        rand = random.random()

        if not self._cmdlist:
            # no commands ready. Load some.

            if not self._loggedin:
                if rand < CHANCE_OF_LOGIN:
                    # get the login commands
                    self._cmdlist = list(makeiter(self._login(self)))
                    NLOGGED_IN += 1  # this is for book-keeping
                    print("connecting client %s (%i/%i)..." % (self.key, NLOGGED_IN, NCLIENTS))
                    self._loggedin = True
                else:
                    # no login yet, so cmdlist not yet set
                    return
            else:
                # we always pick a cumulatively random function
                crand = random.random()
                cfunc = [func for (cprob, func) in self._actions if cprob >= crand][0]
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


# ------------------------------------------------------------
# Access method:
# Starts clients and connects them to a running server.
# ------------------------------------------------------------


def start_all_dummy_clients(nclients):
    """
    Initialize all clients, connect them and start to step them

    Args:
        nclients (int): Number of dummy clients to connect.

    """
    global NCLIENTS
    NCLIENTS = int(nclients)
    actions = DUMMYRUNNER_SETTINGS.ACTIONS

    if len(actions) < 2:
        print(ERROR_FEW_ACTIONS)
        return

    # make sure the probabilities add up to 1
    pratio = 1.0 / sum(tup[0] for tup in actions[2:])
    flogin, flogout, probs, cfuncs = (
        actions[0],
        actions[1],
        [tup[0] * pratio for tup in actions[2:]],
        [tup[1] for tup in actions[2:]],
    )
    # create cumulative probabilies for the random actions
    cprobs = [sum(v for i, v in enumerate(probs) if i <= k) for k in range(len(probs))]
    # rebuild a new, optimized action structure
    actions = (flogin, flogout) + tuple(zip(cprobs, cfuncs))

    # setting up all clients (they are automatically started)
    factory = DummyFactory(actions)
    for i in range(NCLIENTS):
        reactor.connectTCP("localhost", TELNET_PORT, factory)
    # start reactor
    reactor.run()


# ------------------------------------------------------------
# Command line interface
# ------------------------------------------------------------


if __name__ == "__main__":

    try:
        settings.DUMMYRUNNER_MIXIN
    except AttributeError:
        print(ERROR_NO_MIXIN)
        sys.exit()

    # parsing command line with default vals
    parser = ArgumentParser(description=HELPTEXT)
    parser.add_argument(
        "-N", nargs=1, default=1, dest="nclients", help="Number of clients to start"
    )

    args = parser.parse_args()

    print(INFO_STARTING.format(N=args.nclients[0]))

    # run the dummyrunner
    t0 = time.time()
    start_all_dummy_clients(nclients=args.nclients[0])
    ttot = time.time() - t0

    # output runtime
    print("... dummy client runner stopped after %s." % time_format(ttot, style=3))
