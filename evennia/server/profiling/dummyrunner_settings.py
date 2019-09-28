"""
Settings and actions for the dummyrunner

This module defines dummyrunner settings and sets up
the actions available to dummy accounts.

The settings are global variables:

TIMESTEP - time in seconds between each 'tick'
CHANCE_OF_ACTION - chance 0-1 of action happening
CHANCE_OF_LOGIN - chance 0-1 of login happening
TELNET_PORT - port to use, defaults to settings.TELNET_PORT
ACTIONS - see below

ACTIONS is a tuple

(login_func, logout_func, (0.3, func1), (0.1, func2) ... )

where the first entry is the function to call on first connect, with a
chance of occurring given by CHANCE_OF_LOGIN. This function is usually
responsible for logging in the account. The second entry is always
called when the dummyrunner disconnects from the server and should
thus issue a logout command.  The other entries are tuples (chance,
func). They are picked randomly, their commonality based on the
cumulative chance given (the chance is normalized between all options
so if will still work also if the given chances don't add up to 1).
Since each function can return a list of game-command strings, each
function may result in multiple operations.

An action-function is called with a "client" argument which is a
reference to the dummy client currently performing the action. It
returns a string or a list of command strings to execute.  Use the
client object for optionally saving data between actions.

The client object has the following relevant properties and methods:
  key - an optional client key. This is only used for dummyrunner output.
        Default is "Dummy-<cid>"
  cid - client id
  gid - globally unique id, hashed with time stamp
  istep - the current step
  exits - an empty list. Can be used to store exit names
  objs - an empty list. Can be used to store object names
  counter() - returns a unique increasing id, hashed with time stamp
              to make it unique also between dummyrunner instances.

The return should either be a single command string or a tuple of
command strings. This list of commands will always be executed every
TIMESTEP with a chance given by CHANCE_OF_ACTION by in the order given
(no randomness) and allows for setting up a more complex chain of
commands (such as creating an account and logging in).

"""
# Dummy runner settings

# Time between each dummyrunner "tick", in seconds. Each dummy
# will be called with this frequency.
TIMESTEP = 2

# Chance of a dummy actually performing an action on a given tick.
# This spreads out usage randomly, like it would be in reality.
CHANCE_OF_ACTION = 0.5

# Chance of a currently unlogged-in dummy performing its login
# action every tick. This emulates not all accounts logging in
# at exactly the same time.
CHANCE_OF_LOGIN = 1.0

# Which telnet port to connect to. If set to None, uses the first
# default telnet port of the running server.
TELNET_PORT = None


# Setup actions tuple

# some convenient templates

DUMMY_NAME = "Dummy-%s"
DUMMY_PWD = "password-%s"
START_ROOM = "testing_room_start_%s"
ROOM_TEMPLATE = "testing_room_%s"
EXIT_TEMPLATE = "exit_%s"
OBJ_TEMPLATE = "testing_obj_%s"
TOBJ_TEMPLATE = "testing_button_%s"
TOBJ_TYPECLASS = "contrib.tutorial_examples.red_button.RedButton"


# action function definitions (pick and choose from
# these to build a client "usage profile"

# login/logout


def c_login(client):
    "logins to the game"
    # we always use a new client name
    cname = DUMMY_NAME % client.gid
    cpwd = DUMMY_PWD % client.gid

    # set up for digging a first room (to move to and keep the
    # login room clean)
    roomname = ROOM_TEMPLATE % client.counter()
    exitname1 = EXIT_TEMPLATE % client.counter()
    exitname2 = EXIT_TEMPLATE % client.counter()
    client.exits.extend([exitname1, exitname2])

    cmds = (
        "create %s %s" % (cname, cpwd),
        "connect %s %s" % (cname, cpwd),
        "@dig %s" % START_ROOM % client.gid,
        "@teleport %s" % START_ROOM % client.gid,
        "@dig %s = %s, %s" % (roomname, exitname1, exitname2),
    )
    return cmds


def c_login_nodig(client):
    "logins, don't dig its own room"
    cname = DUMMY_NAME % client.gid
    cpwd = DUMMY_PWD % client.gid

    cmds = ("create %s %s" % (cname, cpwd), "connect %s %s" % (cname, cpwd))
    return cmds


def c_logout(client):
    "logouts of the game"
    return "@quit"


# random commands


def c_looks(client):
    "looks at various objects"
    cmds = ["look %s" % obj for obj in client.objs]
    if not cmds:
        cmds = ["look %s" % exi for exi in client.exits]
        if not cmds:
            cmds = "look"
    return cmds


def c_examines(client):
    "examines various objects"
    cmds = ["examine %s" % obj for obj in client.objs]
    if not cmds:
        cmds = ["examine %s" % exi for exi in client.exits]
    if not cmds:
        cmds = "examine me"
    return cmds


def c_idles(client):
    "idles"
    cmds = ("idle", "idle")
    return cmds


def c_help(client):
    "reads help files"
    cmds = ("help", "help @teleport", "help look", "help @tunnel", "help @dig")
    return cmds


def c_digs(client):
    "digs a new room, storing exit names on client"
    roomname = ROOM_TEMPLATE % client.counter()
    exitname1 = EXIT_TEMPLATE % client.counter()
    exitname2 = EXIT_TEMPLATE % client.counter()
    client.exits.extend([exitname1, exitname2])
    return "@dig/tel %s = %s, %s" % (roomname, exitname1, exitname2)


def c_creates_obj(client):
    "creates normal objects, storing their name on client"
    objname = OBJ_TEMPLATE % client.counter()
    client.objs.append(objname)
    cmds = (
        "@create %s" % objname,
        '@desc %s = "this is a test object' % objname,
        "@set %s/testattr = this is a test attribute value." % objname,
        "@set %s/testattr2 = this is a second test attribute." % objname,
    )
    return cmds


def c_creates_button(client):
    "creates example button, storing name on client"
    objname = TOBJ_TEMPLATE % client.counter()
    client.objs.append(objname)
    cmds = ("@create %s:%s" % (objname, TOBJ_TYPECLASS), "@desc %s = test red button!" % objname)
    return cmds


def c_socialize(client):
    "socializechats on channel"
    cmds = (
        "ooc Hello!",
        "ooc Testing ...",
        "ooc Testing ... times 2",
        "say Yo!",
        "emote stands looking around.",
    )
    return cmds


def c_moves(client):
    "moves to a previously created room, using the stored exits"
    cmds = client.exits  # try all exits - finally one will work
    return "look" if not cmds else cmds


def c_moves_n(client):
    "move through north exit if available"
    return "north"


def c_moves_s(client):
    "move through south exit if available"
    return "south"


# Action tuple (required)
#
# This is a tuple of client action functions. The first element is the
# function the client should use to log into the game and move to
# STARTROOM . The second element is the logout command, for cleanly
# exiting the mud. The following elements are 2-tuples of (probability,
# action_function). The probablities should normally sum up to 1,
# otherwise the system will normalize them.
#


# "normal builder" definitionj
# ACTIONS = ( c_login,
#            c_logout,
#            (0.5, c_looks),
#            (0.08, c_examines),
#            (0.1, c_help),
#            (0.01, c_digs),
#            (0.01, c_creates_obj),
#            (0.3, c_moves))
# "heavy" builder definition
# ACTIONS = ( c_login,
#            c_logout,
#            (0.2, c_looks),
#            (0.1, c_examines),
#            (0.2, c_help),
#            (0.1, c_digs),
#            (0.1, c_creates_obj),
#            #(0.01, c_creates_button),
#            (0.2, c_moves))
# "passive account" definition
# ACTIONS = ( c_login,
#            c_logout,
#            (0.7, c_looks),
#            #(0.1, c_examines),
#            (0.3, c_help))
#            #(0.1, c_digs),
#            #(0.1, c_creates_obj),
#            #(0.1, c_creates_button),
#            #(0.4, c_moves))
# "inactive account" definition
# ACTIONS = (c_login_nodig,
#           c_logout,
#           (1.0, c_idles))
# "normal account" definition
ACTIONS = (c_login, c_logout, (0.01, c_digs), (0.39, c_looks), (0.2, c_help), (0.4, c_moves))
# walking tester. This requires a pre-made
# "loop" of multiple rooms that ties back
# to limbo (using @tunnel and @open)
# ACTIONS = (c_login_nodig,
#           c_logout,
#           (1.0, c_moves_n))
# "socializing heavy builder" definition
# ACTIONS = (c_login,
#           c_logout,
#           (0.1, c_socialize),
#           (0.1, c_looks),
#           (0.2, c_help),
#           (0.1, c_creates_obj),
#           (0.2, c_digs),
#           (0.3, c_moves))
# "heavy digger memory tester" definition
# ACTIONS = (c_login,
#           c_logout,
#           (1.0, c_digs))
