"""
Evennia Multidescer

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
`from evennia.contrib.game_systems.multidescer import CmdMultiDesc` to the top.

Next, look up the `at_cmdset_create` method of the `CharacterCmdSet`
class and add a line `self.add(CmdMultiDesc())` to the end
of it.

Reload the server and you should have the +desc command available (it
will replace the default `desc` command).

"""
import re

from evennia import default_cmds
from evennia.utils.eveditor import EvEditor
from evennia.utils.utils import crop

# regex for the set functionality
_RE_KEYS = re.compile(r"([\w\s]+)(?:\+*?)", re.U + re.I)


# Helper functions for the Command


class DescValidateError(ValueError):
    "Used for tracebacks from desc systems"
    pass


def _update_store(caller, key=None, desc=None, delete=False, swapkey=None):
    """
    Helper function for updating the database store.

    Args:
        caller (Object): The caller of the command.
        key (str): Description identifier
        desc (str): Description text.
        delete (bool): Delete given key.
        swapkey (str): Swap list positions of `key` and this key.

    """
    if not caller.db.multidesc:
        # initialize the multidesc attribute
        caller.db.multidesc = [("caller", caller.db.desc or "")]
    if not key:
        return
    lokey = key.lower()
    match = [ind for ind, tup in enumerate(caller.db.multidesc) if tup[0] == lokey]
    if match:
        idesc = match[0]
        if delete:
            # delete entry
            del caller.db.multidesc[idesc]
        elif swapkey:
            # swap positions
            loswapkey = swapkey.lower()
            swapmatch = [ind for ind, tup in enumerate(caller.db.multidesc) if tup[0] == loswapkey]
            if swapmatch:
                iswap = swapmatch[0]
                if idesc == iswap:
                    raise DescValidateError("Swapping a key with itself does nothing.")
                temp = caller.db.multidesc[idesc]
                caller.db.multidesc[idesc] = caller.db.multidesc[iswap]
                caller.db.multidesc[iswap] = temp
            else:
                raise DescValidateError("Description key '|w%s|n' not found." % swapkey)
        elif desc:
            # update in-place
            caller.db.multidesc[idesc] = (lokey, desc)
        else:
            raise DescValidateError("No description was set.")
    else:
        # no matching key
        if delete or swapkey:
            raise DescValidateError("Description key '|w%s|n' not found." % key)
        elif desc:
            # insert new at the top of the stack
            caller.db.multidesc.insert(0, (lokey, desc))
        else:
            raise DescValidateError("No description was set.")


# eveditor save/load/quit functions


def _save_editor(caller, buffer):
    "Called when the editor saves its contents"
    key = caller.db._multidesc_editkey
    _update_store(caller, key, buffer)
    caller.msg("Saved description to key '%s'." % key)
    return True


def _load_editor(caller):
    "Called when the editor loads contents"
    key = caller.db._multidesc_editkey
    match = [ind for ind, tup in enumerate(caller.db.multidesc) if tup[0] == key]
    if match:
        return caller.db.multidesc[match[0]][1]
    return ""


def _quit_editor(caller):
    "Called when the editor quits"
    del caller.db._multidesc_editkey
    caller.msg("Exited editor.")


# The actual command class


class CmdMultiDesc(default_cmds.MuxCommand):
    """
    Manage multiple descriptions

    Usage:
        +desc [key]                - show current desc desc with <key>
        +desc <key> = <text>       - add/replace desc with <key>
        +desc/list                 - list descriptions (abbreviated)
        +desc/list/full            - list descriptions (full texts)
        +desc/edit <key>           - add/edit desc <key> in line editor
        +desc/del <key>            - delete desc <key>
        +desc/swap <key1>-<key2>   - swap positions of <key1> and <key2> in list
        +desc/set <key> [+key+...] - set desc as default or combine multiple descs

    Notes:
        When combining multiple descs with +desc/set <key> + <key2> + ...,
        any keys not matching an actual description will be inserted
        as plain text. Use e.g. ansi line break ||/ to add a new
        paragraph and + + or ansi space ||_ to add extra whitespace.

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
                do_crop = "full" not in switches
                if do_crop:
                    outtext = [
                        "|w%s:|n %s" % (key, crop(desc)) for key, desc in caller.db.multidesc
                    ]
                else:
                    outtext = [
                        "\n|w%s:|n|n\n%s\n%s" % (key, "-" * (len(key) + 1), desc)
                        for key, desc in caller.db.multidesc
                    ]

                caller.msg("|wStored descs:|n\n" + "\n".join(outtext))
                return

            elif "edit" in switches:
                # Use the eveditor to edit/create the named description
                if not args:
                    caller.msg("Usage: %s/edit key" % self.key)
                    return

                # this is used by the editor to know what to edit; it's deleted automatically
                caller.db._multidesc_editkey = args
                # start the editor
                EvEditor(
                    caller,
                    loadfunc=_load_editor,
                    savefunc=_save_editor,
                    quitfunc=_quit_editor,
                    key="multidesc editor",
                    persistent=True,
                )

            elif "delete" in switches or "del" in switches:
                # delete a multidesc entry.
                if not args:
                    caller.msg("Usage: %s/delete key" % self.key)
                    return
                _update_store(caller, args, delete=True)
                caller.msg("Deleted description with key '%s'." % args)

            elif "swap" in switches or "switch" in switches or "reorder" in switches:
                # Reorder list by swapping two entries. We expect numbers starting from 1
                keys = [arg for arg in args.split("-", 1)]
                if not len(keys) == 2:
                    caller.msg("Usage: %s/swap key1-key2" % self.key)
                    return
                key1, key2 = keys
                # perform the swap
                _update_store(caller, key1, swapkey=key2)
                caller.msg("Swapped descs '%s' and '%s'." % (key1, key2))

            elif "set" in switches:
                # switches one (or more) of the multidescs to be the "active" description
                _update_store(caller)
                if not args:
                    caller.msg("Usage: %s/set key [+ key2 + key3 + ...]" % self.key)
                    return
                new_desc = []
                multidesc = caller.db.multidesc
                for key in args.split("+"):
                    notfound = True
                    lokey = key.strip().lower()
                    for mkey, desc in multidesc:
                        if lokey == mkey:
                            new_desc.append(desc)
                            notfound = False
                            continue
                    if notfound:
                        # if we get here, there is no desc match, we add it as a normal string
                        new_desc.append(key)
                new_desc = "".join(new_desc)
                caller.db.desc = new_desc
                caller.msg("%s\n\n|wThe above was set as the current description.|n" % new_desc)

            elif self.rhs or "add" in switches:
                # add text directly to a new entry or an existing one.
                if not (self.lhs and self.rhs):
                    caller.msg("Usage: %s/add key = description" % self.key)
                    return
                key, desc = self.lhs, self.rhs
                _update_store(caller, key, desc)
                caller.msg("Stored description '%s': \"%s\"" % (key, crop(desc)))

            else:
                # display the current description or a numbered description
                _update_store(caller)
                if args:
                    key = args.lower()
                    multidesc = caller.db.multidesc
                    for mkey, desc in multidesc:
                        if key == mkey:
                            caller.msg("|wDecsription %s:|n\n%s" % (key, desc))
                            return
                    caller.msg("Description key '%s' not found." % key)
                else:
                    caller.msg("|wCurrent desc:|n\n%s" % caller.db.desc)

        except DescValidateError as err:
            # This is triggered by _key_to_index
            caller.msg(err)
