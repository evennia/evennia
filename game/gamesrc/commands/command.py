"""
Example command module template

Copy this module up one level to gamesrc/commands/ and name it as
befits your use.  You can then use it as a template to define your new
commands. To use them you also need to group them in a CommandSet (see
examples/cmdset.py)

"""

from ev import Command
from ev import default_cmds
from ev import utils
from ev import Room
import random

class Command(Command):
    """
    Inherit from this if you want to create your own
    command styles. Note that Evennia's default commands
    use MuxCommand instead (next in this module)

    Note that the class's __doc__ string (this text) is
    used by Evennia to create the automatic help entry for
    the command, so make sure to document consistently here.

    """
    # these need to be specified

    key = "MyCommand"
    aliases = ["mycmd", "myc"]
    locks = "cmd:all()"
    help_category = "General"

    # auto_help = False      # uncomment to deactive auto-help for this command.
    # arg_regex = r"\s.*?|$" # optional regex detailing how the part after
                             # the cmdname must look to match this command.

    # (we don't implement hook method access() here, you don't need to
    #  modify that unless you want to change how the lock system works
    #  (in that case see src.commands.command.Command))

    def at_pre_cmd(self):
        """
        This hook is called before self.parse() on all commands
        """
        pass

    def parse(self):
        """
        This method is called by the cmdhandler once the command name
        has been identified. It creates a new set of member variables
        that can be later accessed from self.func() (see below)

        The following variables are available to us:
           # class variables:

           self.key - the name of this command ('mycommand')
           self.aliases - the aliases of this cmd ('mycmd','myc')
           self.locks - lock string for this command ("cmd:all()")
           self.help_category - overall category of command ("General")

           # added at run-time by cmdhandler:

           self.caller - the object calling this command
           self.cmdstring - the actual command name used to call this
                            (this allows you to know which alias was used,
                             for example)
           self.args - the raw input; everything following self.cmdstring.
           self.cmdset - the cmdset from which this command was picked. Not
                         often used (useful for commands like 'help' or to
                         list all available commands etc)
           self.obj - the object on which this command was defined. It is often
                         the same as self.caller.
        """
        pass

    def func(self):
        """
        This is the hook function that actually does all the work. It is called
         by the cmdhandler right after self.parser() finishes, and so has access
         to all the variables defined therein.
        """
        self.caller.msg("Command called!")

    def at_post_cmd(self):
        """
        This hook is called after self.func().
        """
        pass


class MuxCommand(default_cmds.MuxCommand):
    """
    This sets up the basis for a Evennia's 'MUX-like' command
    style. The idea is that most other Mux-related commands should
    just inherit from this and don't have to implement parsing of
    their own unless they do something particularly advanced.

    A MUXCommand command understands the following possible syntax:

      name[ with several words][/switch[/switch..]] arg1[,arg2,...] [[=|,] arg[,..]]

    The 'name[ with several words]' part is already dealt with by the
    cmdhandler at this point, and stored in self.cmdname. The rest is stored
    in self.args.

    The MuxCommand parser breaks self.args into its constituents and stores them
    in the following variables:
      self.switches = optional list of /switches (without the /)
      self.raw = This is the raw argument input, including switches
      self.args = This is re-defined to be everything *except* the switches
      self.lhs = Everything to the left of = (lhs:'left-hand side'). If
                 no = is found, this is identical to self.args.
      self.rhs: Everything to the right of = (rhs:'right-hand side').
                If no '=' is found, this is None.
      self.lhslist - self.lhs split into a list by comma
      self.rhslist - list of self.rhs split into a list by comma
      self.arglist = list of space-separated args (including '=' if it exists)

      All args and list members are stripped of excess whitespace around the
      strings, but case is preserved.
      """

    def func(self):
        """
        This is the hook function that actually does all the work. It is called
        by the cmdhandler right after self.parser() finishes, and so has access
        to all the variables defined therein.
        """
        # this can be removed in your child class, it's just
        # printing the ingoing variables as a demo.
        super(MuxCommand, self).func()

class CmdUse(default_cmds.MuxCommand):
    """
    Use command

    Usage:
        use object [, another object, another object, ...]

        Use object or objects. If more than one object is listed,
        the use command combines all objects to produce one or more
        new objects.

    """
    key = "use"
    locks = "cmd:all()"
    arg_regex = r"\s.*?|$"

    def func(self):
        targets = [t for t in self.lhslist if len(t) > 0]

        # no arguments
        if len(targets) == 0:
            self.caller.msg("Use what?")
            return

        bad_msgs = ["You hurt your finger trying to use {0}.",
                    "As you try to use {0} with the others, it drops and hurts your left foot.", 
                    "While trying to hold {0} steady, it slips and hits you in the face."]
        good_msgs = ["You look closely at {0} but you can't figure out what to do next.",
                "You examine {0} but you have no clue how to go about.",
                "As you shake {0}, you hear rattling noises but nothing else happens."]

        usable_objs = set()
        for t in targets:
            objs = self.caller.search(t, quiet = True)
            if not objs:
                # caller doesn't have it or it's not in caller's location
                self.caller.msg("You don't have any {0}".format(t))
                return
            else:
                if len(objs) > 1:
                    # too many matches
                    self.caller.msg("Among {0} ...".format(",".join([o.name for o in objs])))
                    self.caller.msg("Which one in particular?")
                    return
                else:
                    # one match
                    obj = objs[0]
                    if obj.db.usages and len(obj.db.usages) > 0:
                        # it's usable - somehow
                        usable_objs.add(objs[0])
                    else:
                        # it has no usages
                        self.caller.msg(random.choice(bad_msgs).format(obj))
                        return

        # combine usages (set intersection) to see if they can be used together
        usages = random.choice(list(usable_objs)).db.usages # start with one object usages
        objs_avail = set()
        for uobj in usable_objs:
            print "object:", uobj, "usages:", usages
            usages &= uobj.db.usages
            objs_avail.add(uobj.dbref)
        print "produced usages:", usages
        print "objects avail:", objs_avail
        for usage in usages:
            # usage is the dbref of the object produced 
            # by combining all usable_objs
            prod_obj = self.caller.search(usage)
            objs_needed = prod_obj.db.objs_needed
            usable_objs_names = ", ".join([uo.name for uo in usable_objs])
            if objs_avail.issuperset(objs_needed):
                # all needed are avail (perhaps even some extras)
                for uo in usable_objs:
                    # must put uo inside prod_obj to "hide" it 
                    if uo.dbref in objs_needed:
                        uo.move_to(prod_obj, quiet = True)
                # show success message
                self.caller.msg("You start experimenting with {0} in multiple ways ...".format(usable_objs_names))
                if len(usable_objs) > 1:
                    list_usable_objs = list(usable_objs)
                    self.caller.msg("First {0} ... ".format(list_usable_objs[0].name))
                    for i in range(1, len(list_usable_objs)):
                        self.caller.msg("... then {0} ... ".format(list_usable_objs[i].name))
                voila_msgs = ["Voila", "Eureka", "Awesome", "Genius"]
                self.caller.msg("... {0}!!! \n{1}".format(random.choice(voila_msgs), prod_obj.db.successfully_used_msg))
                if prod_obj.is_typeclass(Room):
                    # a room, teleport into it
                    self.caller.move_to(prod_obj, quiet = True)
                    return
                elif prod_obj.db.is_portable:
                    # portable can be carried around
                    self.caller.msg("You now have {0}.".format(prod_obj.name))
                    prod_obj.move_to(self.caller, quiet = True)
                    return
                else:
                    # let it appear here
                    self.caller.msg("{0} is here now.".format(prod_obj.name))
                    prod_obj.move_to(self.caller.location, quiet = True)
                    return
            else:
                # something's missing
                self.caller.msg(random.choice(good_msgs).format(usable_objs_names))
                self.caller.msg("You are sure that something is missing.")
                return
