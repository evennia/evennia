
"""

Evlang usage examples
 Commands for use with evlang

Evennia contribution - Griatch 2012

The @code command allows to add scripted evlang code to
a ScriptableObject. It will handle access checks.

"""

from ev import utils
from ev import default_cmds
from src.utils import prettytable


#------------------------------------------------------------
# Evlang-related commands
#
# Easiest is to add this command to the default cmdset.
# Alternatively one could imagine storing it directly only
# on scriptable objects.
#------------------------------------------------------------

class CmdCode(default_cmds.MuxCommand):
    """
    add custom code to a scriptable object

    Usage:
      @code[/switch] <obj>[/<type> [= <codestring> ]]

    Switch:

      delete - clear code of given type from the object.
      debug - immediately run the given code after adding it.

    This will add custom scripting to an object
    which allows such modification.

    <type> must be one of the script types allowed
    on the object. Only supplying the command will
    return a list of script types possible to add
    custom scripts to.

    """
    key = "@code"
    locks = "cmd:perm(Builders)"
    help_category = "Building"

    def func(self):
        "implements the functionality."
        caller = self.caller

        if not self.args:
            caller.msg("Usage: @code <obj>[/<type> [= <codestring>]]")
            return
        codetype = None
        objname = self.lhs
        if '/' in self.lhs:
            objname, codetype = [part.strip() for part in self.lhs.rsplit("/", 1)]

        obj = self.caller.search(objname)
        if not obj:
            return

        # get the dicts from db storage for easy referencing
        evlang_scripts = obj.db.evlang_scripts
        evlang_locks = obj.db.evlang_locks
        if not (evlang_scripts != None and evlang_locks and obj.ndb.evlang):
            caller.msg("Object %s can not be scripted." % obj.key)
            return

        if 'delete' in self.switches:
            # clearing a code snippet
            if not codetype:
                caller.msg("You must specify a code type.")
                return
            if not codetype in evlang_scripts:
                caller.msg("Code type '%s' not found on %s." % (codetype, obj.key))
                return
            # this will also update the database
            obj.ndb.evlang.delete(codetype)
            caller.msg("Code for type '%s' cleared on %s." % (codetype, obj.key))
            return

        if not self.rhs:
            if codetype:
                scripts = [(name, tup[1], utils.crop(tup[0]))
                     for name, tup in evlang_scripts.items() if name==codetype]
                scripts.extend([(name, "--", "--") for name in evlang_locks
                               if name not in evlang_scripts if name==codetype])
            else:
                # no type specified. List all scripts/slots on object
                print evlang_scripts
                scripts = [(name, tup[1], utils.crop(tup[0]))
                                        for name, tup in evlang_scripts.items()]
                scripts.extend([(name, "--", "--") for name in evlang_locks
                                                if name not in evlang_scripts])
                scripts = sorted(scripts, key=lambda p: p[0])

            table = prettytable.PrettyTable(["{wtype", "{wcreator", "{wcode"])
            for tup in scripts:
                table.add_row([tup[0], tup[1], tup[2]])
            string = "{wEvlang scripts on %s:{n\n%s" % (obj.key, table)
            caller.msg(string)
            return

        # we have rhs
        codestring = self.rhs
        if not codetype in evlang_locks:
            caller.msg("Code type '%s' cannot be coded on %s." % (codetype, obj.key))
            return
        # check access with the locktype "code"
        if not obj.ndb.evlang.lockhandler.check(caller, "code"):
            caller.msg("You are not permitted to add code of type %s." % codetype)
            return
        # we have code access to this type.
        oldcode = None
        if codetype in evlang_scripts:
            oldcode = str(evlang_scripts[codetype][0])
        # this updates the database right away too
        obj.ndb.evlang.add(codetype, codestring, scripter=caller)
        if oldcode:
            caller.msg("{wReplaced{n\n %s\n{wWith{n\n %s" % (oldcode, codestring))
        else:
            caller.msg("Code added in '%s':\n %s" % (codetype, codestring))
        if "debug" in self.switches:
            # debug mode
            caller.msg("{wDebug: running script (look out for errors below) ...{n\n" + "-"*68)
            obj.ndb.evlang.run_by_name(codetype, caller, quiet=False)
