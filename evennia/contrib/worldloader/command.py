"""
Commands

Add three commands: @importcsv, @datainfo and @batchbuilder

"""

import os
import re
from django.conf import settings
from django.db.models.loading import get_model
from loader import import_csv, set_obj_data_info
from builder import build_all
from evennia import Command as BaseCommand
from evennia import default_cmds
from evennia.utils import create, utils, search
from worlddata import world_settings


class Command(BaseCommand):
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

    # optional
    # auto_help = False      # uncomment to deactive auto-help for this command.
    # arg_regex = r"\s.*?|$" # optional regex detailing how the part after
                             # the cmdname must look to match this command.

    # (we don't implement hook method access() here, you don't need to
    #  modify that unless you want to change how the lock system works
    #  (in that case see evennia.commands.command.Command))

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


#------------------------------------------------------------
# import csv tables
#------------------------------------------------------------
class CmdImportCsv(MuxCommand):
    """
    Usage:
      @importcsv
      
      <modelname> must be in world_settings.CSV_DATA.
      If <modelname> is empty, it will import all csv files in world_settings.CSV_DATA.
    """
    key = "@importcsv"
    locks = "perm(Builders)"
    help_cateogory = "Builders"
    arg_regex = r"\s.*?|$"

    def func(self):
        "Implement the command"
    
        caller = self.caller
        
        # count the number of files loaded
        count = 0
        
        # get app_name
        app_name = world_settings.WORLD_DATA_APP
        
        # get model_name, can specify the model name in args
        # if no args is given, load all models in settings.WORLD_DATA
        models = self.args
        if models:
            models = [arg.strip() for arg in models.split(',')]
        else:
            models = world_settings.WORLD_DATA

        # import models one by one
        for model_name in models:
            # can only import models in world_settings.WORLD_DATA
            if not model_name in world_settings.WORLD_DATA:
                caller.msg("%s is not in world_settings.WORLD_DATA, cannot import." % model_name)
                continue

            # make file name
            file_name = os.path.join(world_settings.CSV_DATA_PATH, model_name + ".csv")
            
            # import data
            try:
                import_csv(file_name, app_name, model_name)
                caller.msg("%s imported." % model_name)
                count += 1
            except Exception, e:
                print e
                continue

        caller.msg("total %d files imported." % count)


#------------------------------------------------------------
# set object's info_db and info_key
#------------------------------------------------------------
class CmdSetDataInfo(MuxCommand):
    """
    Usage:
    @datainfo <obj>[=<key>]
    
    This will set the data key to an object.
    @datainfo <obj> will show the data key of the object.
    """
    key = "@datainfo"
    locks = "perm(Builders)"
    help_cateogory = "Building"
    
    def func(self):
        """
        Implement the command
        """
        caller = self.caller
        if not self.args:
            string = "Usage: @datainfo <obj>[=<key>]"
            caller.msg(string)
            return
        
        if not self.rhs:
            if self.args == self.lhs:
                # no "="
                obj_name = self.args
                obj = caller.search(obj_name, location=caller.location)
                if not obj:
                    caller.msg("Sorry, can not find %s." % obj_name)
                elif obj.db.info_db and obj.db.info_key:
                    caller.msg("%s's datainfo is %s" % (obj_name, obj.db.info_db + "." + obj.db.info_key))
                else:
                    caller.msg("%s has no datainfo." % obj_name)
                return

        obj_name = self.lhs
        obj = caller.search(obj_name, location=caller.location)
        if not obj:
            caller.msg("Sorry, can not find %s." % obj_name)
            return

        # set the key:
        key_name = self.rhs
        model_name = ""
        app_name = ""
        
        if key_name:
            for model in world_settings.WORLD_DATA:
                model_obj = get_model(world_settings.WORLD_DATA_APP, model)
                if model_obj:
                    if model_obj.objects.filter(key=key_name):
                        model_name = model
                        app_name = world_settings.WORLD_DATA_APP
                        break

        try:
            set_obj_data_info(obj, app_name, model_name, key_name)
            caller.msg("%s's datainfo has been set to %s" % (obj_name, self.rhs))
        except Exception, e:
            caller.msg("Can't set datainfo %s to %s: %s" % (self.rhs, obj_name, e))


#------------------------------------------------------------
# batch builder
#------------------------------------------------------------
class CmdBatchBuilder(MuxCommand):
    """
    Usage:
      @batchbuilder
      
    Build the whole game world with data in CSV files.
    """
    key = "@batchbuilder"
    aliases = ["@batchbld"]
    locks = "perm(Builders)"
    help_cateogory = "Builders"
    arg_regex = r"\s.*?|$"

    def func(self):
        "Implement the command"
        build_all(self.caller)

