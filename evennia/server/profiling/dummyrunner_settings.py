"""
Settings and actions for the dummyrunner

This module defines dummyrunner settings and sets up
the actions available to dummy accounts.

The settings are global variables:

- TIMESTEP - time in seconds between each 'tick'. 1 is a good start.
- CHANCE_OF_ACTION - chance 0-1 of action happening. Default is 0.5.
- CHANCE_OF_LOGIN - chance 0-1 of login happening. 0.01 is a good number.
- TELNET_PORT - port to use, defaults to settings.TELNET_PORT
- ACTIONS - see below

ACTIONS is a tuple

```python
(login_func, logout_func, (0.3, func1), (0.1, func2) ... )

```

where the first entry is the function to call on first connect, with a
chance of occurring given by CHANCE_OF_LOGIN. This function is usually
responsible for logging in the account. The second entry is always
called when the dummyrunner disconnects from the server and should
thus issue a logout command. The other entries are tuples (chance,
func). They are picked randomly, their commonality based on the
cumulative chance given (the chance is normalized between all options
so if will still work also if the given chances don't add up to 1).

The PROFILE variable define pre-made ACTION tuples for convenience.

Each function should return an iterable of one or more command-call
strings (like "look here"), so each can group multiple command operations.

An action-function is called with a "client" argument which is a
reference to the dummy client currently performing the action.

The client object has the following relevant properties and methods:

- key - an optional client key. This is only used for dummyrunner output.
  Default is "Dummy-<cid>"
- cid - client id
- gid - globally unique id, hashed with time stamp
- istep - the current step
- exits - an empty list. Can be used to store exit names
- objs - an empty list. Can be used to store object names
- counter() - returns a unique increasing id, hashed with time stamp
  to make it unique also between dummyrunner instances.

The return should either be a single command string or a tuple of
command strings. This list of commands will always be executed every
TIMESTEP with a chance given by CHANCE_OF_ACTION by in the order given
(no randomness) and allows for setting up a more complex chain of
commands (such as creating an account and logging in).

----

"""
import random
import string

# Dummy runner settings

# Time between each dummyrunner "tick", in seconds. Each dummy
# will be called with this frequency.
TIMESTEP = 1
# TIMESTEP = 0.025  # 40/s

# Chance of a dummy actually performing an action on a given tick.
# This spreads out usage randomly, like it would be in reality.
CHANCE_OF_ACTION = 0.5

# Chance of a currently unlogged-in dummy performing its login
# action every tick. This emulates not all accounts logging in
# at exactly the same time.
CHANCE_OF_LOGIN = 0.01

# Which telnet port to connect to. If set to None, uses the first
# default telnet port of the running server.
TELNET_PORT = None


# Setup actions tuple

# some convenient templates

DUMMY_NAME = "Dummy_{gid}"
DUMMY_PWD = (
    "".join(random.choice(string.ascii_letters + string.digits) for _ in range(20)) + "-{gid}"
)
START_ROOM = "testing_room_start_{gid}"
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
    cname = DUMMY_NAME.format(gid=client.gid)
    cpwd = DUMMY_PWD.format(gid=client.gid)
    room_name = START_ROOM.format(gid=client.gid)

    # we assign the dummyrunner cmdsert to ourselves so # we can use special commands
    add_cmdset = (
        "py from evennia.server.profiling.dummyrunner import DummyRunnerCmdSet;"
        "self.cmdset.add(DummyRunnerCmdSet, persistent=False)"
    )

    # create character, log in, then immediately dig a new location and
    # teleport it (to keep the login room clean)
    cmds = (
        f"create {cname} {cpwd}",
        f"yes",  # to confirm creation
        f"connect {cname} {cpwd}",
        f"dig {room_name}",
        f"teleport {room_name}",
        add_cmdset,
    )
    return cmds


def c_login_nodig(client):
    "logins, don't dig its own room"
    cname = DUMMY_NAME.format(gid=client.gid)
    cpwd = DUMMY_PWD.format(gid=client.gid)
    cmds = (f"create {cname} {cpwd}", f"connect {cname} {cpwd}")
    return cmds


def c_logout(client):
    "logouts of the game"
    return ("quit",)


# random commands


def c_looks(client):
    "looks at various objects"
    cmds = ["look %s" % obj for obj in client.objs]
    if not cmds:
        cmds = ["look %s" % exi for exi in client.exits]
        if not cmds:
            cmds = ("look",)
    return cmds


def c_examines(client):
    "examines various objects"
    cmds = ["examine %s" % obj for obj in client.objs]
    if not cmds:
        cmds = ["examine %s" % exi for exi in client.exits]
    if not cmds:
        cmds = ("examine me",)
    return cmds


def c_idles(client):
    "idles"
    cmds = ("idle", "idle")
    return cmds


def c_help(client):
    "reads help files"
    cmds = (
        "help",
        "dummyrunner_echo_response",
    )
    return cmds


def c_digs(client):
    "digs a new room, storing exit names on client"
    roomname = ROOM_TEMPLATE % client.counter()
    exitname1 = EXIT_TEMPLATE % client.counter()
    exitname2 = EXIT_TEMPLATE % client.counter()
    client.exits.extend([exitname1, exitname2])
    return ("dig/tel %s = %s, %s" % (roomname, exitname1, exitname2),)


def c_creates_obj(client):
    "creates normal objects, storing their name on client"
    objname = OBJ_TEMPLATE % client.counter()
    client.objs.append(objname)
    cmds = (
        "create %s" % objname,
        'desc %s = "this is a test object' % objname,
        "set %s/testattr = this is a test attribute value." % objname,
        "set %s/testattr2 = this is a second test attribute." % objname,
    )
    return cmds


def c_creates_button(client):
    "creates example button, storing name on client"
    objname = TOBJ_TEMPLATE % client.counter()
    client.objs.append(objname)
    cmds = ("create %s:%s" % (objname, TOBJ_TYPECLASS), "desc %s = test red button!" % objname)
    return cmds


def c_socialize(client):
    "socializechats on channel"
    cmds = (
        "pub Hello!",
        "say Yo!",
        "emote stands looking around.",
    )
    return cmds


def c_moves(client):
    "moves to a previously created room, using the stored exits"
    cmds = client.exits  # try all exits - finally one will work
    return ("look",) if not cmds else cmds


def c_moves_n(client):
    "move through north exit if available"
    return ("north",)


def c_moves_s(client):
    "move through south exit if available"
    return ("south",)


def c_measure_lag(client):
    """
    Special dummyrunner command, injected in c_login. It  measures
    response time. Including this in the ACTION tuple will give more
    dummyrunner output about just how fast commands are being processed.

    The dummyrunner will treat this special and inject the
    {timestamp} just before sending.

    """
    return ("dummyrunner_echo_response {timestamp}",)


# Action profile (required)

# Some pre-made profiles to test. To make your own, just assign a tuple to ACTIONS.
#
# idler - does nothing after logging in
# looker - just looks around
# normal_player - moves around, reads help, looks around (digs rarely) (spammy)
# normal_builder -  digs now and then, examines, creates objects, moves
# heavy_builder - digs and creates a lot, moves and examines
# socializing_builder - builds a lot, creates help entries, moves, chat (spammy)
# only_digger - extreme builder that only digs room after room

PROFILE = "looker"


if PROFILE == "idler":
    ACTIONS = (
        c_login,
        c_logout,
        (0.9, c_idles),
        (0.1, c_measure_lag),
    )
elif PROFILE == "looker":
    ACTIONS = (c_login, c_logout, (0.8, c_looks), (0.2, c_measure_lag))
elif PROFILE == "normal_player":
    ACTIONS = (
        c_login,
        c_logout,
        (0.01, c_digs),
        (0.29, c_looks),
        (0.2, c_help),
        (0.3, c_moves),
        (0.05, c_socialize),
        (0.1, c_measure_lag),
    )
elif PROFILE == "normal_builder":
    ACTIONS = (
        c_login,
        c_logout,
        (0.5, c_looks),
        (0.08, c_examines),
        (0.1, c_help),
        (0.01, c_digs),
        (0.01, c_creates_obj),
        (0.2, c_moves),
        (0.1, c_measure_lag),
    )
elif PROFILE == "heavy_builder":
    ACTIONS = (
        c_login,
        c_logout,
        (0.1, c_looks),
        (0.1, c_examines),
        (0.2, c_help),
        (0.1, c_digs),
        (0.1, c_creates_obj),
        (0.2, c_moves),
        (0.1, c_measure_lag),
    )
elif PROFILE == "socializing_builder":
    ACTIONS = (
        c_login,
        c_logout,
        (0.1, c_socialize),
        (0.1, c_looks),
        (0.1, c_help),
        (0.1, c_creates_obj),
        (0.2, c_digs),
        (0.3, c_moves),
        (0.1, c_measure_lag),
    )
elif PROFILE == "only_digger":
    ACTIONS = (c_login, c_logout, (0.9, c_digs), (0.1, c_measure_lag))

else:
    print("No dummyrunner ACTION profile defined.")
    import sys

    sys.exit()
