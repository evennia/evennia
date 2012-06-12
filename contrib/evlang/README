
EVLANG

EXPERIMENTAL IMPLEMENTATION

Evennia contribution - Griatch 2012

"Evlang" is a heavily restricted version of Python intended to be used
by regular players to code simple functionality on supporting objects.
It's referred to as "evlang" or "evlang scripts" in order to
differentiate from Evennia's normal (and unrelated) "Scripts".

WARNING:
 Restricted python execution is a tricky art, and this module -is-
 partly based on blacklisting techniques, which might be vulnerable to
 new venues of attack opening up in the future (or existing ones we've
 missed). Whereas I/we know of no obvious exploits to this, it is no
 guarantee. If you are paranoid about security, consider also using
 secondary defences on the OS level such as a jail and highly
 restricted execution abilities for the twisted process. So in short,
 this should work fine, but use it at your own risk. You have been
 warned.

An Evennia server with Evlang will, once set up, minimally consist of
the following components:

  - The evlang parser (bottom of evlang.py). This combines
    regular removal of dangerous modules/builtins with AST-traversal.
    it implements a limited_exec() function.
  - The Evlang handler (top of evlang.py). This handler is the Evennia
    entry point. It should be added to objects that should support
    evlang-scripting.
  - A custom object typeclass. This must set up the Evlang handler
    and store a few critical Attributes on itself for book-keeping.
    The object will probably also overload some of its hooks to
    call the correct evlang script at the proper time
  - Command(s) for adding code to supporting objects
  - Optional expanded "safe" methods/objects to include in the
    execution environment. These are defined in settings (see
    header of evlang.py for more info).

You can set this up easily to try things out by using the included
examples:

Quick Example Install
---------------------

This is a quick test-setup using the example objects and commands.

1) If you haven't already, make sure you are able to overload the
   default cmdset: Copy game/gamesrc/commands/examples/cmdset.py up
   one level, then change settings.CMDSET_DEFAULT to point to
   DefaultCmdSet in your newly copied module.  Restart the server and
   check so the default commands still work.
2) Import and add
      contrib.evlang.command.CmdCode
      and
      contrib.evlang.examples.CmdCraftScriptable
   to your default command set. Reload server.

That's it, really. You should now have two new commands available,
@craftscriptable and @code. The first one is a simple "crafting-like"
command that will create an object of type
contrib.evlang.examples.CraftedScriptableObject while setting it up
with some basic scripting slots.

Try it now:

 @craftscriptable crate

You create a simple "crate" object in your current location. You can
use @code to see which "code types" it will accept.

 @code crate

You should see a list with "drop", "get" and "look", each without
anything assigned to them.  If you look at how CraftedScriptableObject
is defined you will find that these "command types" (you can think of
them as slots where custom code can be put) are tied to the at_get,
at_drop and at_desc hooks respecively - this means Evlang scripts put
in the respective slots will ttrigger at the appropriate time.

There are a few "safe" objects made available out of the box.

 self - reference to object the Evlang handler is defined on
 here - shortcut for self.location
 caller - reference back to the one triggering the script
 scripter - reference to the one creating the script (set by @code)

 There is also the 'evl' object that defines "safe" methods to use:

 evl.msg(string, obj=None)                 # default is the send to caller
 evl.msg_contents(string, obj=None)        # default is to send to all except caller
 evl.msg_home(string, obj=None)            # default is to send to self.location
 delay(delay, function, *args, **kwargs)
 attr(obj, attrname=None, attrvalue=None, delete=False)  # lock-checking attribute accesser
 list()  # display all available methods on evl, with docstrings (including your custom additions)

These all return True after successful execution, which makes
especially the msg* functions easier to use in a conditional. Let's
try it.

 @code crate/look = caller.key=='Superman' and evl.msg("Your gaze burns a small hole.") or evl.msg("Looks robust!")

Now look at the crate. :)

You can (in evlang) use evl.list() to get a list of all methods
currently stored on the evl object. For testing, let's use the same
look slot on the crate again. But this time we'll use the /debug mode
of @code, which means the script will be auto-run immediately and we
don't have to look at the create to get a result when developing.

@code/debug crate/look = evl.msg(evl.list())

