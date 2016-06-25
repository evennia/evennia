"""
Evennia Mutltidescer

Contrib - Griatch 2016

A "multidescer" is a concept from the MUSH world. It allows for
creating, managing and switching between multiple character
descriptions. This multidescer will not require any changes to the
Character class, rather it will use the `multidescs` Attribute (a
list) and create it if it does not exist.

This contrib also works well together with the rpsystem contrib (which
also adds the short descriptions and the `sdesc` command).


Installation:

Edit `mygame/commands/default_cmdsets.py` and add
`from contrib.multidesc import CmdMultiDesc` to the top.

Next, look up the `at_cmdset_create` method of the `CharacterCmdSet`
class and add a line `self.add(CmdMultiDesc())` to the end
of it.

Reload the server and you should have the +desc command available (it
will replace the default `desc` command).

"""
from evennia import default_cmds
from evennia.utils.utils import crop
from evennia.utils.eveditor import EvEditor


# Helper functions for the Command


def _update_store(caller, num=0, text=None, replace=False):
    """
    Helper function for updating the database store.

    Args:
        caller (Object): The caller of the command.
        num (int): Index of store to update.
        text (str): Description text.
        replace (bool): Replace or amend description.

    """
    if not caller.db.multidesc:
        # initialize the multidesc attribute
        caller.db.multidesc = [caller.db.desc or ""]
    if not text:
        return
    if replace:
        caller.db.multidesc[num] = text
    else:
        caller.db.multidesc.insert(num, text)


class NumValidateError(ValueError):
    "Used for tracebacks from _validate_num"
    pass


def _validate_num(caller, num):
    """
    Check so the given num is a valid number in the storage interval.

    Args:
        caller (Object): The caller of the command
        num (str): The number to validate.

    Returns:
        num (int): Returns the valid index (starting from 0)

    Raises:
        NumValidateError: For malformed numbers.

    Notes:
        This function will also report errors.

    """
    if not caller.db.multidesc:
        _update_store(caller)
    nlen = len(caller.db.multidesc)
    if not num.strip().isdigit() or not (0 < int(num) <= nlen):
        raise NumValidateError("%s must be a number between 1 and %i." %
                                ('%s' % num or "Argument", nlen))
    else:
        return int(num) - 1


# eveditor save/load/quit functions

def _save_editor(caller, buffer):
    "Called when the editor saves its contents"
    num = caller.db._multidesc_editnum
    replace = caller.db._multidesc_editreplace
    if num is not None:
        _update_store(caller, num, buffer, replace=replace)
        caller.msg("Saved the buffer to description slot %i." % (num + 1))
        return True

def _load_editor(caller):
    "Called when the editor loads contents"
    num = caller.db._multidesc_editnum
    if num is not None:
        try:
            return caller.db.multidesc[num]
        except IndexError:
            pass
    return ""

def _quit_editor(caller):
    "Called when the editor quits"
    del caller.db._multidesc_editnum
    del caller.db._multidesc_editreplace
    caller.msg("Exited editor.")


# The actual command class

class CmdMultiDesc(default_cmds.MuxCommand):
    """
    Manage multiple descriptions

    Usage:
        +desc [n]                - show current or desc <n>
        +desc/list               - list descriptions (abbreviated)
        +desc/list/full          - list descriptions (full texts)
        +desc/add [<n> =] <text> - add new desc or replace desc <n>
        +desc/edit [n]           - open editor to modify current or desc <n>
        +desc/del [n]            - delete current or desc <n>
        +desc/swap <n1>-<n2>     - reorder list by swapping #n1 and <n2>
        +desc/set <n>            - set which desc <n> as active desc

    """
    key = "+desc"
    aliases = ["desc"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        """
        Implements the multidescer.  We will use `db.desc` for the
        description in use and `db.multidesc` to store all descriptions.
        """

        caller = self.caller
        args = self.args.strip()
        switches = self.switches

        try:
            if "list" in switches or "all" in switches:
                # list all stored descriptions, either in full or cropped.
                # Note that we list starting from 1, not from 0.
                _update_store(caller)
                do_crop = not "full" in switches
                outtext = "|wStored descs:|n"
                for inum, desc in enumerate(caller.db.multidesc):
                    outtext += "\n|w%i:|n %s" % (inum + 1, crop(desc) if do_crop else "\n%s" % desc)
                caller.msg(outtext)

            elif "add" in switches:
                # add text directly to a new entry or an existing one.
                if self.rhs:
                    # this means a '=' was given
                    num, desc = _validate_num(caller, self.lhs), self.rhs
                    replace = True
                else:
                    num, desc = 0, self.args
                    replace = False
                if not desc:
                    caller.msg("No description given.")
                    return
                _update_store(caller, num, desc, replace=replace)
                caller.msg("Stored description in slot %i: \"%s\"" % (num + 1, crop(desc)))

            elif "edit" in switches:
                # Use the eveditor to edit the description.
                if args:
                    num = _validate_num(caller, args)
                    replace = True
                else:
                    num = 1
                    replace = False
                # this is used by the editor to know what to edit; it's deleted automatically
                caller.db._multidesc_editnum = num
                caller.db._multidesc_editreplace = replace
                # start the editor
                EvEditor(caller, loadfunc=_load_editor, savefunc=_save_editor,
                         quitfunc=_quit_editor, key="multidesc editor", persistent=True)

            elif "delete" in switches or "del" in switches:
                # delete a multidesc entry.
                num = _validate_num(caller, args)
                del caller.db.multidesc[num]
                caller.msg("Deleted description number %i." % (num + 1))

            elif "swap" in switches or "switch" in switches or "reorder" in switches:
                # Reorder list by swapping two entries. We expect numbers starting from 1
                nums = [_validate_num(caller, arg) for arg in args.split("-", 1)]
                if not len(nums) == 2:
                    caller.msg("To swap two desc entries, use |w%s/swap <num1> - <num2>|n" % (self.key))
                    return
                num1, num2 = nums
                if num1 == num2:
                    caller.msg("Swapping position with itself changes nothing.")
                    return
                # perform the swap
                desc1, desc2 = caller.db.multidesc[num1], caller.db.multidesc[num2]
                caller.db.multidesc[num2] = desc1
                caller.db.multidesc[num1] = desc2
                caller.msg("Swapped descs numbers %i and %i." % (num1 + 1, num2 + 1))

            elif "set" in switches:
                # switches one of the multidescs to be the "active",
                # description, with numbers starting from 1
                if args:
                    num = _validate_num(caller, args)
                else:
                    _update_store(caller)
                    num = 0
                # activating this description
                caller.db.desc = caller.db.multidesc[num]
                caller.msg("|wSet description %i as the current one:|n\n%s" % (num + 1, crop(caller.db.desc)))

            else:
                # display the current description or a numbered description
                if args:
                    num = _validate_num(caller, args)
                    caller.msg("|wDecsription number %i:|n\n%s" % (num + 1, caller.db.multidesc[num]))
                else:
                    caller.msg("|wCurrent desc:|n\n%s" % caller.db.desc)

        except NumValidateError, err:
            # This is triggered by _validate_num
            caller.msg(err)
