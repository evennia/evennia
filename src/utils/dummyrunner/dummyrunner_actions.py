"""
These are actions for the dummy client runner, using
the default command set and intended for unmodified Evennia.

Each client action is defined as a function. The clients
will perform these actions randomly (except the login action).

Each action-definition function should take one argument- "client",
which is a reference to the client currently performing the action
Use the client object for saving data between actions.

The client object has the following relevant properties and methods:
  cid - unique client id
  istep - the current step
  exits - an empty list. Can be used to store exit names
  objs - an empty list. Can be used to store object names
  counter() - get an integer value. This counts up for every call and
              is always unique between clients.

The action-definition function should return the command that the
client should send to the server (as if it was input in a mud client).
It should also return a string detailing the action taken. This string is
used by the "brief verbose" mode of the runner and is prepended by
"Client N " to produce output like "Client 3 is creating objects ..."

This module *must* also define a variable named ACTIONS. This is a tuple
where the first element is the function object for the action function
to call when the client logs onto the server.  The following elements
are 2-tuples (probability, action_func), where probability defines how
common it is for that particular action to happen. The runner will
randomly pick between those functions based on the probability.

ACTIONS = (login_func, (0.3, func1), (0.1, func2) ... )

To change the runner to use your custom ACTION and/or action
definitions, edit settings.py and add

 DUMMYRUNNER_ACTIONS_MODULE = "path.to.your.module"

"""

# it's very useful to have a unique id for this run to avoid any risk
# of clashes

import time
RUNID = time.time()

# some convenient templates

START_ROOM = "testing_room_start-%s-%s" % (RUNID, "%i")
ROOM_TEMPLATE = "testing_room_%s-%s" % (RUNID, "%i")
EXIT_TEMPLATE = "exit_%s-%s" % (RUNID, "%i")
OBJ_TEMPLATE = "testing_obj_%s-%s" % (RUNID, "%i")
TOBJ_TEMPLATE = "testing_button_%s-%s" % (RUNID, "%i")
TOBJ_TYPECLASS = "examples.red_button.RedButton"

# action function definitions

def c_login(client):
    "logins to the game"
    cname = "Dummy-%s-%i" % (RUNID, client.cid)
    #cemail = "%s@dummy.com" % (cname.lower())
    cpwd = "%s-%s" % (RUNID, client.cid)
    # set up for digging a first room (to move to)
    roomname = ROOM_TEMPLATE % client.counter()
    exitname1 = EXIT_TEMPLATE % client.counter()
    exitname2 = EXIT_TEMPLATE % client.counter()
    client.exits.extend([exitname1, exitname2])
    #cmd = '@dig %s = %s, %s' % (roomname, exitname1, exitname2)
    cmd = ('create %s %s' % (cname, cpwd),
           'connect %s %s' % (cname, cpwd),
           '@dig %s' % START_ROOM % client.cid,
           '@teleport %s' % START_ROOM % client.cid,
           '@dig %s = %s, %s' % (roomname, exitname1, exitname2)
           )

    return cmd, "logs in as %s ..." % cname

def c_logout(client):
    "logouts of the game"
    return "@quit", "logs out"

def c_looks(client):
    "looks at various objects"
    cmd = ["look %s" % obj for obj in client.objs]
    if not cmd:
        cmd = ["look %s" % exi for exi in client.exits]
        if not cmd:
            cmd = "look"
    return cmd, "looks ..."

def c_examines(client):
    "examines various objects"
    cmd = ["examine %s" % obj for obj in client.objs]
    if not cmd:
        cmd = ["examine %s" % exi for exi in client.exits]
    if not cmd:
        cmd = "examine me"
    return cmd, "examines objs ..."

def c_help(client):
    "reads help files"
    cmd = ('help',
           'help @teleport',
           'help look',
           'help @tunnel',
           'help @dig')
    return cmd, "reads help ..."

def c_digs(client):
    "digs a new room, storing exit names on client"
    roomname = ROOM_TEMPLATE % client.counter()
    exitname1 = EXIT_TEMPLATE % client.counter()
    exitname2 = EXIT_TEMPLATE % client.counter()
    client.exits.extend([exitname1, exitname2])
    cmd = '@dig %s = %s, %s' % (roomname, exitname1, exitname2)
    return cmd, "digs ..."

def c_creates_obj(client):
    "creates normal objects, storing their name on client"
    objname = OBJ_TEMPLATE % client.counter()
    client.objs.append(objname)
    cmd = ('@create %s' % objname,
           '@desc %s = "this is a test object' % objname,
           '@set %s/testattr = this is a test attribute value.' % objname,
           '@set %s/testattr2 = this is a second test attribute.' % objname)
    return cmd, "creates obj ..."

def c_creates_button(client):
    "creates example button, storing name on client"
    objname = TOBJ_TEMPLATE % client.counter()
    client.objs.append(objname)
    cmd = ('@create %s:%s' % (objname, TOBJ_TYPECLASS),
           '@desc %s = test red button!' % objname)
    return cmd, "creates button ..."

def c_socialize(client):
    "socializechats on channel"
    cmd = ('ooc Hello!',
          'ooc Testing ...',
          'ooc Testing ... times 2',
          'say Yo!',
          'emote stands looking around.')
    return cmd, "socializes ..."

def c_moves(client):
    "moves to a previously created room, using the stored exits"
    cmd = client.exits # try all exits - finally one will work
    if not cmd: cmd = "look"
    return cmd, "moves ..."


# Action tuple (required)
#
# This is a tuple of client action functions. The first element is the
# function the client should use to log into the game and move to
# STARTROOM . The second element is the logout command, for cleanly
# exiting the mud. The following elements are 2-tuples of (probability,
# action_function). The probablities should normally sum up to 1,
# otherwise the system will normalize them.
#

## "normal builder" definition
#ACTIONS = ( c_login,
#            c_logout,
#            (0.5, c_looks),
#            (0.08, c_examines),
#            (0.1, c_help),
#            (0.01, c_digs),
#            (0.01, c_creates_obj),
#            #(0.1, c_creates_button),
#            (0.3, c_moves))
## "heavy" builder definition
#ACTIONS = ( c_login,
#            c_logout,
#            (0.2, c_looks),
#            (0.1, c_examines),
#            (0.2, c_help),
#            (0.1, c_digs),
#            (0.1, c_creates_obj),
#            #(0.01, c_creates_button),
#            (0.2, c_moves))
## "passive player" definition
#ACTIONS = ( c_login,
#            c_logout,
#            (0.7, c_looks),
#            #(0.1, c_examines),
#            (0.3, c_help))
#            #(0.1, c_digs),
#            #(0.1, c_creates_obj),
#            #(0.1, c_creates_button),
#            #(0.4, c_moves))
## "socializing heavy builder" definition
ACTIONS = (c_login,
           c_logout,
           (0.1, c_socialize),
           (0.1, c_looks),
           (0.1, c_help),
           (0.2, c_creates_obj),
           (0.2, c_digs),
           (0.3, c_moves))
