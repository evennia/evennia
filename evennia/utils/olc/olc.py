"""
OLC - On-Line Creation

This module is the core of the Evennia online creation helper system.
This is a resource intended for players with build privileges.

While the OLC command can be used to start the OLC "from the top", the
system is also intended to be plugged in to enhance existing build commands
with a more menu-like building style.

Functionality:

- Prototype management: Allows to create and edit Prototype
dictionaries. Can store such Prototypes on the Builder Player as an Attribute
or centrally on a central store that all builders can fetch prototypes from.
- Creates a new entity either from an existing prototype or by creating the
prototype on the fly for the sake of that single object (the prototype can
then also be saved for future use).
- Recording of session, for performing a series of recorded build actions in sequence.
Stored so as to be possible to reproduce.
- Export of objects created in recording mode to a batchcode file (Immortals only).


"""

from time import time
from collections import OrderedDict
from evennia.utils.evmenu import EvMenu
from evennia.commands.command import Command


# OLC settings
_SHOW_PROMPT = True   # settings.OLC_SHOW_PROMPT
_DEFAULT_PROMPT = ""  # settings.OLC_DEFAULT_PROMPT
_LEN_HISTORY = 10     # settings.OLC_HISTORY_LENGTH


# OLC Session

def _new_session():

    """
    This generates an empty olcsession structure, which is used to hold state
    information in the olc but which can also be pickled.

    Returns:
        olcsession (dict): An empty OLCSession.

    """
    return {
        # header info
        "caller": None,                                 # the current user of this session
        "modified": time(),
        "db_model": None,                               # currently unused, ObjectDB for now
        "prompt_template": _DEFAULT_PROMPT,             # prompt display
        "olcfields": OrderedDict(),                                # registered OLCFields. Order matters
        "prototype_key": "",                            # current active prototype key
    }


def _update_prompt(osession):
    """
    Update the OLC status prompt.

    Returns:
        prompt (str): The prompt based on the
            prompt template, populated with
            the olcsession state.

    """
    return ""


def search_entity(osession, query):
    """
    Perform a query for a specified entity. Which type of entity is determined by the osession
    state.

    Args:
        query (str): This is a string, a #dbref or an extended search

    """
    pass




def display_prototype(osession):
    """
    Display prototype fields according to the order of the registered olcfields.

    """
    # TODO: Simple one column display to begin with - make multi-column later
    pkey = osession['prototype_key']
    outtxt = ["=== {pkey} ===".format(pkey=pkey)]
    for field in osession['olcfields'].values():
        fname, flabel, fvalue = field.name, field.label, field.display()
        outtxt.append("  {fieldname} ({label}): {value}".format(fieldname=fname,
                                                                label=flabel, value=fvalue))
    return '\n'.join(outtxt)


def display_field_value(osession, fieldname):
    """
    Display info about a specific field.
    """
    field = osession['olcfields'].get(fieldname, None)
    if field:
        return "{fieldname}: {value}".format(fieldname=field.name, value=field.display())


# Access function

from evennia.utils.olc import olc_pages
def display_obj(obj):
    """
    Test of displaying object using fields and pages.
    """
    olcsession = _new_session()
    olcsession['caller'] = obj
    page = olc_pages.OLCObjectPage(olcsession)
    obj.msg(str(page))



def OLC(caller, target=None, startnode=None):
    """
    This function is a common entry-point into the OLC menu system. It is used
    by Evennia systems to jump into the different possible start points of the
    OLC menu tree depending on what info is already available.

    Args:
        caller (Object or Player): The one using the olc.
        target (Object, optional): Object to operate on, if any is known.
        startnode (str, optional): Where in the menu tree to start. If unset,
            will be decided by whether target is given or not.

    """
    startnode = startnode or (target and "node_edit_top") or "node_top"
    EvMenu(caller, "evennia.utils.olc.olc_menu", startnode=startnode, target=target)


class CmdOLC(Command):
    """
    Test OLC

    Usage:
      olc [target]

    Starts the olc to create a new object or to modify an existing one.

    """
    key = "olc"
    def func(self):
        OLC(self.caller, target=self.args)

