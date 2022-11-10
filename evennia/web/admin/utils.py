"""
Helper utils for admin views.

"""

import importlib

from evennia.utils.utils import get_all_cmdsets, get_all_typeclasses, inherits_from


def get_and_load_typeclasses(parent=None, excluded_parents=None):
    """
    Get all typeclasses. We we need to initialize things here
    for them to be actually available in the admin process.
    This is intended to be used with forms.ChoiceField.

    Args:
        parent (str or class, optional): Limit selection to this class and its children
            (at any distance).
        exclude (list): Class-parents to exclude from the resulting list. All
            children of these paretns will be skipped.

    Returns:
        list: A list of (str, str), the way ChoiceField wants it.

    """
    # this is necessary in order to have typeclasses imported and accessible
    # in the inheritance tree.
    import evennia

    evennia._init()

    # this return a dict (path: class}
    tmap = get_all_typeclasses(parent=parent)

    # filter out any excludes
    excluded_parents = excluded_parents or []
    tpaths = [
        path
        for path, tclass in tmap.items()
        if not any(inherits_from(tclass, excl) for excl in excluded_parents)
    ]

    # sort so we get custom paths (not in evennia repo) first
    tpaths = sorted(tpaths, key=lambda k: (1 if k.startswith("evennia.") else 0, k))

    # the base models are not typeclasses so we filter them out
    tpaths = [
        path
        for path in tpaths
        if path
        not in (
            "evennia.objects.models.ObjectDB",
            "evennia.accounts.models.AccountDB",
            "evennia.scripts.models.ScriptDB",
            "evennia.comms.models.ChannelDB",
        )
    ]

    # return on form excepted by ChoiceField
    return [(path, path) for path in tpaths if path]


def get_and_load_cmdsets(parent=None, excluded_parents=None):
    """
    Get all cmdsets available or as children based on a parent cmdset.  We need
    to initialize things here to make sure as much as possible is loaded in the
    admin process. This is intended to be used with forms.ChoiceField.

    Args:
        parent (str, optional): Python-path to the parent cmdset, if any.
        excluded_parents (list): A list of cmset-paths to exclude from the result.

    Returns:
        list: A list of (str, str), the way ChoiceField wants it.

    """
    # we must do this to have cmdsets imported and accessible in the inheritance tree.
    import evennia

    evennia._init()

    cmap = get_all_cmdsets(parent)

    excluded_parents = excluded_parents or []
    cpaths = [path for path in cmap if not any(path == excluded for excluded in excluded_parents)]

    cpaths = sorted(cpaths, key=lambda k: (1 if k.startswith("evennia.") else 0, k))

    # return on form expected by ChoiceField
    return [("", "-")] + [(path, path) for path in cpaths if path]
