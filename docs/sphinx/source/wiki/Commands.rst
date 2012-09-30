Command system
==============

The basic way for users to communicate with the game is through
*Commands*. These can be commands directly related to the game world
such as *look*, *get*, *drop* and so on, or administrative commands such
as *examine* or *@dig*.

The `default commands <DefaultCommandHelp.html>`_ coming with Evennia
are 'MUX-like' in that they use @ for admin commands, support things
like switches, syntax with the '=' symbol etc, but there is nothing that
prevents you from implementing a completely different command scheme for
your game. You can find the default commands in
``src/commands/default``. You should not edit these directly - they will
be updated by the Evennia team as new features are added. Rather you
should look to them for inspiration and inherit your own designs from
them.

There are two components to having a command running - the *Command*
class and the *Command Set*.

A *Command* is a python class containing all the functioning code for
what a command does - for example, a *get* command would contain code
for picking up objects.

A *Command Set* (often referred to as a CmdSet) is like a container for
one or more Commands. A given Command can go into any number of
different command sets. By putting the command set on a character object
you will make all the commands therein available to use by that
character. You can also store command sets on normal objects if you want
users to be able to use the object in various ways. Consider a "Tree"
object with a cmdset defining the commands *climb* and *chop down*. Or a
"Clock" with a cmdset containing the single command *check time*.

This page goes into full detail about how to use Commands. There is also
a step-by-step `beginner's tutorial <AddingCommandTutorial.html>`_ that
will get you started quickly without the explanations.

Defining a Command
------------------

All commands are implemented as normal Python classes inheriting from
the base class ``Command`` (``ev.Command``). You will find that this
base class is very "bare". The default commands of Evennia actually
inherit from a child of ``Command`` called ``MuxCommand`` - this is the
class that knows all the mux-like syntax like ``/switches``, splitting
by "=" etc. Below we'll avoid mux-specifics and use the base ``Command``
class directly.

::

    # basic Command definition
    from ev import Command
    class MyCmd(Command):
       """
       This is the help-text for the command
       """
       key = "mycommand" 
       def parse(self):
           # parsing the command line here
       def func(self):
           # executing the command here 

You define a new command by assigning a few class-global properties on
your inherited class and overloading one or two hook functions. The full
gritty mechanic behind how commands work are found towards the end of
this page; for now you only need to know that the command handler
creates an instance of this class and uses that instance whenever you
use this command - it also dynamically assigns the new command instance
a few useful properties that you can assume to always be available.

Properties assigned to the command instance at run-time
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say player *Bob* with a character *BigGuy* enters the command
*look at sword*. After the system having successfully identified this a
the "look" command and determined that *BigGuy* really has access to a
command named ``look``, it chugs the ``look`` command class out of
storage and either loads an existing Command instance from cache or
creates one. After some more checks it then assigns it the following
properties:

-  ``caller`` - a reference to the object executing the command - this
   is normally the Character\_BigGuy\_, not his Player *Bob* ! If you
   want to do something to the player (*Bob*) in your command, do so
   through ``caller.player``. (Since cmdsets can be put directly on
   Players, caller *can* be a Player object as well, such commands are
   usually quite specific though).
-  ``cmdstring`` - the matched key for the command. This would be *look*
   in our example.
-  ``args`` - this is the rest of the string, except the command name.
   So if the string entered was *look at sword*, ``args`` would be "*at
   sword*\ ".
-  ``obj`` - the game `Object <Objects.html>`_ on which this command is
   defined. This need not be the caller, but since ``look`` is a common
   (default) command, this is probably defined directly on *BigGuy* - so
   ``obj`` will point to BigGuy. Otherwise ``obj`` could be a Player or
   any interactive object with commands defined on it, like in the
   example of the "check time" command defined on a "Clock" object or a
   `red
   button <https://code.google.com/p/evennia/source/browse/trunk/game/gamesrc/objects/examples/red_button.py>`_
   that you can "``push``\ ".
-  ``cmdset`` - this is a reference to the merged CmdSet (see below)
   from which this command was matched. This variable is rarely used,
   it's main use is for the `auto-help system <HelpSystem.html>`_
   (*Advanced note: the merged cmdset need NOT be the same as
   BigGuy.cmdset. The merged set can be a combination of the cmdsets
   from other objects in the room, for example*).
-  ``raw_string`` - this is the raw input coming from the user, without
   stripping any surrounding whitespace. The only thing that is stripped
   is the ending newline marker.

Defining your own command classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beyond the properties Evennia always assigns to the command at runtime
(listed above), your job is to define the following class properties:

-  ``key`` (string) - the identifier for the command, like ``look``.
   This should (ideally) be unique. A key can consist of more than one
   word, like "press button" or "pull left lever".
-  ``aliases`` (optional list) - a list of alternate names for the
   command (``["l", "glance", "see"]``). Same name rules as for ``key``
   applies.
-  ``locks`` (string) - a `lock definition <Locks.html>`_, usually on
   the form ``cmd:<lockfuncs>``. Locks is a rather big topic, so until
   you learn more about locks, stick to giving the lockstring
   ``"cmd:all()"`` to make the command available to everyone (if you
   don't put a lock string, this will be assigned for you).
-  ``help_category`` (optional string) - setting this helps to structure
   the auto-help into categories. If none is set, this will be set to
   *General*.
-  ``save_for_next`` (optional boolean). This defaults to ``False``. If
   ``True``, a copy of this command object (along with any changes you
   have done to it) will be stored by the system and can be accessed by
   the next command by retrieving ``self.caller.ndb.last_cmd``. The next
   run command will either clear or replace the storage.
-  'arg\_regex' (optional raw string): This should be given as a `raw
   regular expression string <http://docs.python.org/library/re.html>`_.
   The regex will be compiled by the system at runtime. This allows you
   to customize how the part *immediately following* the command name
   (or alias) must look in order for the parser to match for this
   command. Normally the parser is highly efficient in picking out the
   command name, also as the beginning of a longer word (as long as the
   longer word is not a command name in it self). So ``"lookme"`` will
   be parsed as the command ``"look"`` followed by the argument
   ``"me"``. By using ``arg_regex`` you could for example force the
   parser to require a space to follow the command name (regex string
   for this would be ``r"\s.*?|$"``). In that case, only ``"look me"``
   will work whereas ``"lookme"`` will lead to an "command not found"
   error.
-  auto\_help (optional boolean). Defaults to ``True``. This allows for
   turning off the
   [`HelpSystem <HelpSystem.html>`_\ #Command\_Auto-help\_system
   auto-help system] on a per-command basis. This could be useful if you
   either want to write your help entries manually or hide the existence
   of a command from ``help``'s generated list.

You should also implement at least two methods, ``parse()`` and
``func()`` (You could also implement ``perm()``, but that's not needed
unless you want to fundamentally change how access checks work).

``parse()`` is intended to parse the arguments (``self.args``) of the
function. You can do this in any way you like, then store the result(s)
in variable(s) on the command object itself (i.e. on ``self``). To take
an example, the default mux-like system uses this method to detect
"command switches" and store them as a list in ``self.switches``. Since
the parsing is usually quite similar inside a command scheme you should
make ``parse()`` as generic as possible and then inherit from it rather
than re-implementing it over and over. In this way, the default
``MuxCommand`` class implements a ``parse()`` for all child commands to
use.

``func()`` is called right after ``parse()`` and should make use of the
pre-parsed input to actually do whatever the command is supposed to do.
This is the main body of the command.

Finally, you should always make an informative `doc
string <http://www.python.org/dev/peps/pep-0257/#what-is-a-docstring>`_
(``__doc__``) at the top of your class. This string is dynamically read
by the `Help system <HelpSystem.html>`_ to create the help entry for
this command. You should decide on a way to format your help and stick
to that.

Below is how you define a simple alternative "``smile``\ " command:

::

    from ev import Command

    class CmdSmile(Command):
        """
        A smile command

        Usage: 
          smile [at] [<someone>]
          grin [at] [<someone>] 

        Smiles to someone in your vicinity or to the room
        in general.

        (This initial string (the __doc__ string)
        is also used to auto-generate the help 
        for this command)
        """ 
      
        key = "smile"
        aliases = ["smile at", "grin", "grin at"] 
        locks = "cmd:all()"
        help_category = "General"
      
        def parse(self):
            "Very trivial parser" 
            self.target = self.args.strip() 

        def func(self):
            "This actually does things"
            caller = self.caller
            if not self.target or self.target == "here":
                string = "%s smiles." % caller.name
                caller.location.msg_contents(string, exclude=caller)
                caller.msg("You smile.")
            else:
                target = self.search(self.target)
                if not target: 
                    # self.search handles error messages
                    return
                string = "%s smiles to you." % caller.name
                target.msg(string)
                string = "You smile to %s." % target.name
                caller.msg(string)
                string = "%s smiles to %s." % (caller.name, target.name)           
                caller.location.msg_contents(string, exclude=[caller,target])

The power of having commands as classes and to separate ``parse()`` and
``func()`` lies in the ability to inherit functionality without having
to parse every command individually. For example, as mentioned the
default commands all inherit from ``MuxCommand``. ``MuxCommand``
implements its own version of ``parse()`` that understands all the
specifics of MUX-like commands. Almost none of the default commands thus
need to implement ``parse()`` at all, but can assume the incoming string
is already split up and parsed in suitable ways by its parent.

Command Sets
------------

All commands in Evennia are always grouped together into *Command Sets*
(CmdSets). A particular ``Command`` class definition can be part of any
number of different CmdSets. CmdSets can be stored either on game
`Objects <Objects.html>`_ or on `Players <Players.html>`_.

When a user issues a command, it is matched against the contents of all
cmdsets available to the user at the moment,
[Commands#Adding\_and\_merging\_command\_sets merged together]. The
currently valid command sets are collected from the following sources,
in this order:

-  The active cmdset on the character object
-  The cmdsets of objects carried by the character
-  The cmdset of the current location
-  The cmdset(s) of objects in the current location (this includes
   exits)
-  The channel commandset
-  The cmdset defined on the Player object controlling the character
   (OOC cmdset)

The default ``CmdSet`` shipping with Evennia is automatically added to
all new characters and contains commands such as ``look``, ``drop``,
``@dig`` etc. You can find it defined in
``src/commands/default/cmdset_default.py``, but it is also referenced by
importing ``ev.default_cmds`` and accessing its property
``DefaultCmdset``. Players have an Out-of-character cmdset called
``cmdset_ooc`` that can also be found from the same place. There is
finally an "unloggedin" cmdset that is used before the Player has
authenticated to the game. The path to these three standard command sets
are defined in settings, as ``CMDSET_UNLOGGEDIN``, ``CMDSET_DEFAULT``
and ``CMDSET_OOC``. You can create any number of command sets besides
those to fit your needs.

A CmdSet is, as most things in Evennia, defined as a Python class
inheriting from the correct parent (``ev.CmdSet`` or
``src.commands.cmdset.CmdSet``). The CmdSet class only needs to define
one method, called ``at_cmdset_creation()``. All other class parameters
are optional, but are used for more advanced set manipulation and coding
(see the [Commands#Merge\_rules merge rules] section).

::

    from ev import CmdSet
    from game.gamesrc.commands import mycommands
    class MyCmdSet(CmdSet):    
        def at_cmdset_creation(self):
            """
            The only thing this method should need
            to do is to add commands to the set.                                        
            """     
            self.add(mycommands.MyCommand1())
            self.add(mycommands.MyCommand2())
            self.add(mycommands.MyCommand3())       

The CmdSet's ``add()`` method can also take another CmdSet as input. In
this case all the commands from that CmdSet will be appended to this one
as if you added them line by line:

::

       at_cmdset_creation(): 
           ...
           self.add(AdditionalCmdSet) # adds all command from this set
           ...

If you added your command to an existing cmdset (like to the default
cmdset), that set is already loaded into memory. You need to make the
server aware of the code changes:

::

    @reload 

You should now be able to use the command.

If you created a new, fresh cmdset, this must be added to an object in
order to make the commands within available. A simple way to temporarily
test a cmdset on yourself is use the ``@py`` command to execute a python
snippet:

::

    @py self.cmdset.add('game.gamesrc.commands.mycmdset.MyCmdSet')

This will stay with you until you ``@reset`` or ``@shutdown`` the
server, or you run

::

    @py self.cmdset.delete('game.gamesrc.commands.mycmdset.MyCmdSet')

For a quick tutorial on setting up things more permanently read the
`Step by step
tutorial <http://code.google.com/p/evennia/wiki/AddingCommandTutorial>`_
for a different way of approaching it. Generally you can customize which
command sets are added to your objects by using ``self.cmdset.add()`` or
``self.cmdset.add_default()``.

Adding and merging command sets
-------------------------------

*Note: This is an advanced topic. It's useful to know about, but you
might want to skip it if this is your first time learning about
commands.*

CmdSets have the special ability that they can be *merged* together into
new sets. This would happen if you, for example, did
``object.cmdset.add(MyCmdSet)`` on an object that already had a command
set defined on it. The two sets will be evaluated and a temporary,
*merged set* will be created out of the commands in both sets. Only the
commands in this merged set is from that point available to use. Which
of the ingoing commands end up in the merged set is defined by the
*merge rule* and the relative *priorities* of the two sets. Removing the
latest added set will restore things back to the way it was before the
addition.

CmdSets are non-destructively stored in a stack inside the cmdset
handler on the object. This stack is parsed to create the "combined"
cmdset active at the moment. The very first cmdset in this stack is
called the *Default cmdset* and is protected from accidental deletion.
Running ``obj.cmdset.delete()`` will never delete the default set.
Instead one should add new cmdsets on top of the default to "hide" it,
as described below. Use the special ``obj.cmdset.delete_default()`` only
if you really know what you are doing.

CmdSet merging is an advanced feature useful for implementing powerful
game effects. Imagine for example a player entering a dark room. You
don't want the player to be able to find everything in the room at a
glance - maybe you even want them to have a hard time to find stuff in
their backpack! You can then define a different CmdSet with commands
that override the normal ones. While they are in the dark room, maybe
the ``look`` and ``inv`` commands now just tell the player they cannot
see anything! Another example would be to offer special combat commands
only when the player is in combat. Or when being on a boat. Or when
having taken the super power-up. All this can be done on the fly by
merging command sets.

Merge rules
~~~~~~~~~~~

To understand how sets merge, we need to define a little lingo. Let's
call the first command set **A** and the second **B**. We will merge
**A** onto **B**, so in code terms the command would be
``object.cdmset.add(A)``, where we assume **B** was already the active
cmdset on ``object`` since earlier.

We let the **A** set have higher priority than **B**. A priority is
simply an integer number. Default is 0, Evennia's in-built high-prio
commands (intended to overrule others) have values of 9 or 10.

Both sets contain a number of commands named by numbers, like ``A1, A2``
for set **A** and ``B1, B2, B3, B4`` for **B**. So for that example both
sets contain commands with the same keys 1 and 2, whereas commands 3 and
4 are unique to **B**. To describe a merge between these sets, we would
write ``A1,A2 + B1,B2,B3,B4 = ?`` where ``?`` is a list of commands that
depend on which merge type **A** has, and which relative priorities the
two sets have. By convention, we read this statement as "New command set
**A** is merged onto the old command set **B** to form **?**".

Below are the available merge types and how they work. Names are partly
borrowed from `Set theory <http://en.wikipedia.org/wiki/Set_theory>`_.

**Union** (default) - The two cmdsets are merged so that as many
commands as possible from each cmdset ends up in the merged cmdset.
Same-key commands are merged by priority.

::

    # Union
    A1,A2 + B1,B2,B3,B4 = A1,A2,B3,B4

**Intersect** - Only commands found in *both* cmdsets (i.e. which have
the same keys) end up in the merged cmdset, with the higher-priority
cmdset replacing the lower one's commands.

::

    # Intersect 
    A1,A3,A5 + B1,B2,B4,B5 = A1,A5

**Replace** - The commands of the higher-prio cmdset completely replaces
the lower-priority cmdset's commands, regardless of if same-key commands
exist or not.

::

    # Replace
    A1,A3 + B1,B2,B4,B5 = A1,A3

**Remove** - The high-priority command sets removes same-key commands
from the lower-priority cmdset. They are not replaced with anything, so
this is a sort of filter that prunes the low-prio set using the
high-prio one as a template.

::

    # Remove
    A1,A3 + B1,B2,B3,B4,B5 = B2,B4,B5

Besides ``priority`` and ``mergetype``, a command set also takes a few
other variables to control how they merge:

-  *allow\_duplicates* (bool) - determines what happens when two sets of
   equal priority merge. Default is that the new set in the merger (i.e.
   **A** above) automatically takes precedence. But if
   *allow\_duplicates* is true, the result will be a merger with more
   than one of each name match. This will usually lead to the player
   receiving a multiple-match error higher up the road, but can be good
   for things like cmdsets on non-player objects in a room, to allow the
   system to warn that more than one 'ball' in the room has the same
   'kick' command defined on it, so it may offer a chance to select
   which ball to kick ... Allowing duplicates only makes sense for
   *Union* and *Intersect*, the setting is ignored for the other
   mergetypes.
-  *key\_mergetype* (dict) - allows the cmdset to define a unique
   mergetype for particular cmdsets, identified by their cmdset-key.
   Format is ``{CmdSetkey:mergetype}``. Priorities still apply. Example:
   ``{'Myevilcmdset','Replace'}`` which would make sure for this set to
   always use 'Replace' on ``Myevilcmdset`` only, no matter what
   *mergetype* is set to.

More advanced cmdset example:

::

    class MyCmdSet(CmdSet):

        key = "MyCmdSet"
        priority = 4
        mergetype = "Replace"
        key_mergetype = {'MyOtherCmdSet':'Union'}  

        def at_cmdset_creation(self):
            """
            The only thing this method should need
            to do is to add commands to the set.                                        
            """     
            self.add(mycommands.MyCommand1())
            self.add(mycommands.MyCommand2())
            self.add(mycommands.MyCommand3())       

System commands
---------------

*Note: This is an advanced topic. Skip it if this is your first time
learning about commands.*

There are several command-situations that are exceptional in the eyes of
the server. What happens if the player enters an empty string? What if
the 'command' given is infact the name of a channel the user wants to
send a message to? Or if there are multiple command possibilities?

Such 'special cases' are handled by what's called *system commands*. A
system command is defined in the same way as other commands, except that
their name (key) must be set to one reserved by the engine (the names
are defined at the top of ``src/commands/cmdhandler.py``). You can find
(unused) implementations of the system commands in
``src/commands/default/system_commands.py``. Since these are not (by
default) included in any ``CmdSet`` they are not actually used, they are
just there for show. When the special situation occurs, Evennia will
look through all valid ``CmdSet``\ s for your custom system command.
Only after that will it resort to its own, hard-coded implementation.

Here are the exceptional situations that triggers system commands. You
can find the command keys they use as properties on ``ev.syscmdkeys``

-  No input (``syscmdkeys.CMD_NOINPUT``) - the player just pressed
   return without any input. Default is to do nothing, but it can be
   useful to do something here for certain implementations such as line
   editors that interpret non-commands as text input (an empty line in
   the editing buffer).
-  Command not found (``syscmdkeys.CMD_NOMATCH``) - No matching command
   was found. Default is to display the "Huh?" error message.
-  Several matching commands where found (``syscmdkeys.CMD_MULTIMATCH``)
   - Default is to show a list of matches.
-  User is not allowed to execute the command
   (``syscmdkeys.CMD_NOPERM``) - Default is to display the "Huh?" error
   message.
-  Channel (``syscmdkeys.CMD_CHANNEL``) - This is a
   `Channel <Communications.html>`_ name of a channel you are
   subscribing to - Default is to relay the command's argument to that
   channel. Such commands are created by the Comm system on the fly
   depending on your subscriptions.
-  New session connection ('syscmdkeys.CMD\_LOGINSTART'). This command
   name should be put in the ``settings.CMDSET_UNLOGGEDIN``. Whenever a
   new connection is established, this command is always called on the
   server (default is to show the login screen).

Below is an example of redefining what happens when the player don't
give any input (e.g. just presses return). Of course the new system
command must be added to a cmdset as well before it will work.

::

    from ev import syscmdkeys, Command

    class MyNoInputCommand(Command):
        "Usage: Just press return, I dare you"
        key = syscmdkeys.CMD_NOINPUT
        def func(self):
            self.caller.msg("Don't just press return like that, talk to me!")

Exits
-----

*Note: This is an advanced topic.*

The functionality of `Exit <Objects.html>`_ objects in Evennia is not
hard-coded in the engine. Instead Exits are normal typeclassed objects
that auto-creates a ``CmdSet`` on themselves when they are loaded. This
cmdset has a single command with the same name (and aliases) as the Exit
object itself. So what happens when a Player enters the name of the Exit
on the command line is simply that the command handler, in the process
of searching all available commands, also picks up the command from the
Exit object(s) in the same room. Having found the matching command, it
executes it. The command then makes sure to do all checks and eventually
move the Player across the exit as appropriate. This allows exits to be
extremely flexible - the functionality can be customized just like one
would edit any other command.

Admittedly, you will usually be fine just using the appropriate
``traverse_*`` hooks. But if you are interested in really changing how
things work under the hood, check out ``src.objects.objects`` for how
the default ``Exit`` typeclass is set up.

How commands actually work
--------------------------

*Note: This is an advanced topic mainly of interest to server
developers.*

Any time the user sends text to Evennia, the server tries to figure out
if the text entered corresponds to a known command. This is how the
command handler sequence looks for a logged-in user:

#. A user (the *caller*) enters a string of text and presses enter.

   -  If input is an empty string, resend command as ``CMD_NOINPUT``. If
      no such command is found in cmdset, ignore.
   -  If command.key matches ``settings.IDLE_COMMAND``, update timers
      but don't do anything more.

#. Evennia's *commandhandler* gathers the CmdSets available to *caller*
   at the time:

   -  The caller's own currently active CmdSet.
   -  The active CmdSets of eventual objects in the same location (if
      any). This includes commands on [Objects#Exits Exits].
   -  Sets of dynamically created *System commands* representing
      available `Channels <Communications.html>`_.
   -  CmdSet defined on the *caller.player* (OOC cmdset).

#. All the CmdSets are *merged* into one combined CmdSet according to
   each set's merge rules.
#. Evennia's *command parser* takes the merged cmdset and matches each
   of its commands (using its key and aliases) against the beginning of
   the string entered by *caller*. This produces a set of candidates.
#. The *cmd parser* next rates the matches by how many characters they
   have and how many percent matches the respective known command. Only
   if candidates cannot be separated will it return multiple matches.

   -  If multiple matches were returned, resend as ``CMD_MULTIMATCH``.
      If no such command is found in cmdset, return hard-coded list of
      matches.
   -  If no match was found, resend as ``CMD_NOMATCH``. If no such
      command is found in cmdset, give hard-coded error message.

#. If a single command was found by the parser, the correct command
   class is plucked out of storage and instantiated.
#. It is checked that the caller actually has access to the command by
   validating the *lockstring* of the command. If not, it is not
   considered as a suitable match it is resent as ``CMD_NOPERM`` is
   created. If no such command is found in cmdset, use hard-coded error
   message.
#. If the new command is tagged as a channel-command, resend as
   ``CMD_CHANNEL``. If no such command is found in cmdset, use
   hard-coded implementation.
#. Assign several useful variables to the command instance.
#. Call ``at_pre_command()`` on the command instance.
#. Call ``parse()`` on the command instance. This is is fed the
   remainder of the string, after the name of the command. It's intended
   to pre-parse the string int a form useful for the ``func()`` method.
#. Call ``func()`` on the command instance. This is the functional body
   of the command, actually doing useful things.
#. Call ``at_post_command()`` on the command instance.

Assorted notes
--------------

The return value of ``Command.func()`` is a Twisted
`deferred <http://twistedmatrix.com/documents/current/core/howto/defer.html>`_.
Evennia does not use this return value at all by default. If you do, you
must thus do so asychronously, using callbacks.

::

     # in command class func()
     def callback(ret, caller):
        caller.msg("Returned is %s" % ret)
     deferred = self.execute_command("longrunning")
     deferred.addCallback(callback, self.caller)

This is probably not relevant to any but the most advanced/exotic
designs (one might use it to create a "nested" command structure for
example).

The ``save_for_next`` class variable can be used to implement
state-persistent commands. For example it can make a command operate on
"it", where it is determined by what the previous command operated on.
