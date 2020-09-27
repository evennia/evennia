"""
Game tutor

Evennia contrib - Griatch 2020

This contrib is a system for easily adding a tutor/tutorial for your game
(something that should be considered a necessity for any game ...).

It consists of a single room that will be created for each player/character
wanting to go through the tutorial. The text is presented as a menu of
self-sustained 'lessons' that the user can either jump freely between or step
through wizard-style. In each lesson, the tutor will track progress (for
example the user may be asked to try out a certain command, and the tutor will
not move on until that command has been tried).
::
    # node Start

    Neque ea alias perferendis molestiae eligendi. Debitis exercitationem
    exercitationem quas blanditiis quisquam officia ut. Fugit aut fugit enim quia
    non. Earum et excepturi animi ex esse accusantium et. Id adipisci eos enim
    ratione.

    ## options

    1: first option -> node1
    2: second option -> node2
    3: node3 -> gotonode3()
    next;n: node2
    top: start
    >input: return to go back -> start
    >input foo*: foo()
    >input bar*: bar()

    # node node1

    Neque ea alias perferendis molestiae eligendi. Debitis exercitationem
    exercitationem quas blanditiis quisquam officia ut. Fugit aut fugit enim quia
    non. Earum et excepturi animi ex esse accusantium et. Id adipisci eos enim
    ratione.

    ...

"""

import re
from ast import literal_eval

from evennia import EvMenu
from fnmatch import fnmatch
# i18n
from django.utils.translation import gettext as _

_RE_NODE = re.compile(r"#\s*?NODE\s+?(?P<nodename>\S+?)$", re.I + re.M)
_RE_OPTIONS_SEP = re.compile(r"##\s*?OPTIONS\s*?$", re.I + re.M)
_RE_CALLABLE = re.compile(r"\S+?\(\)", re.I + re.M)
_RE_CALLABLE = re.compile(
    r"(?P<funcname>\S+?)(?:\((?P<kwargs>[\S\s]+?=[\S\s]+?)\)|\(\))", re.I+re.M)

_HELP_NO_OPTION_MATCH = _("Choose an option or try 'help'.")

_OPTION_INPUT_MARKER = ">"
_OPTION_ALIAS_MARKER = ";"
_OPTION_SEP_MARKER = ":"
_OPTION_CALL_MARKER = "->"
_OPTION_COMMENT_START = "#"


# Input/option/goto handler functions that allows for dynamically generated
# nodes read from the menu template.

def _generated_goto_func(caller, raw_string, **kwargs):
    goto = kwargs['goto']
    goto_callables = kwargs['goto_callables']
    current_nodename = kwargs['current_nodename']

    if _RE_CALLABLE.match(goto):
        gotofunc = goto.strip()[:-2]
        if gotofunc in goto_callables:
            goto = goto_callables[gotofunc](caller, raw_string, **kwargs)
    if goto is None:
        return goto, {"generated_nodename": current_nodename}
    caller.msg(_HELP_NO_OPTION_MATCH)
    return goto, {"generated_nodename": goto}


def _generated_input_goto_func(caller, raw_string, **kwargs):
    gotomap = kwargs['gotomap']
    goto_callables = kwargs['goto_callables']
    current_nodename = kwargs['current_nodename']

    # start with glob patterns
    for pattern, goto in gotomap.items():
        if fnmatch(raw_string.lower(), pattern):
            match = _RE_CALLABLE.match(goto)
            print(f"goto {goto} -> match: {match}")
            if match:
                gotofunc = match.group("funcname")
                gotokwargs = match.group("kwargs") or ""
                print(f"gotofunc: {gotofunc}, {gotokwargs}")
                if gotofunc in goto_callables:
                    for kwarg in gotokwargs.split(","):
                        if kwarg and "=" in kwarg:
                            print(f"kwarg {kwarg}")
                            key, value = [part.strip() for part in kwarg.split("=", 1)]
                            try:
                                key = literal_eval(key)
                            except ValueError:
                                pass
                            try:
                                value = literal_eval(value)
                            except ValueError:
                                pass
                            kwargs[key] = value
                    goto = goto_callables[gotofunc](caller, raw_string, **kwargs)
            if goto is None:
                return goto, {"generated_nodename": current_nodename}
            return goto, {"generated_nodename": goto}
    # no glob pattern match; try regex
    for pattern, goto in gotomap.items():
        if re.match(pattern, raw_string.lower(), flags=re.I + re.M):
            if _RE_CALLABLE.match(goto):
                gotofunc = goto.strip()[:-2]
                if gotofunc in goto_callables:
                    goto = goto_callables[gotofunc](caller, raw_string, **kwargs)
            if goto is None:
                return goto, {"generated_nodename": current_nodename}
            return goto, {"generated_nodename": goto}
    # no match, rerun current node
    caller.msg(_HELP_NO_OPTION_MATCH)
    return None, {"generated_nodename": current_nodename}


def _generated_node(caller, raw_string, generated_nodename="", **kwargs):
    text, options = caller.db._generated_menu_contents[generated_nodename]
    return text, options


def parse_menu_template(caller, menu_template, goto_callables=None):
    """
    Parse menu-template string

    Args:
        caller (Object or Account): Entity using the menu.
        menu_template (str): Menu described using the templating format.
        goto_callables (dict, optional): Mapping between call-names and callables
            on the form `callable(caller, raw_string, **kwargs)`. These are what is
            available to use in the `menu_template` string.

    """

    def _parse_options(nodename, optiontxt, goto_callables):
        """
        Parse option section into option dict.
        """
        options = []
        optiontxt = optiontxt[0].strip() if optiontxt else ""
        optionlist = [optline.strip() for optline in optiontxt.split("\n")]
        inputparsemap = {}

        for inum, optline in enumerate(optionlist):
            if (optline.startswith(_OPTION_COMMENT_START)
                    or _OPTION_SEP_MARKER not in optline):
                # skip comments or invalid syntax
                continue
            key = ""
            desc = ""
            pattern = None

            key, goto = [part.strip() for part in optline.split(_OPTION_SEP_MARKER, 1)]

            # desc -> goto
            if _OPTION_CALL_MARKER in goto:
                desc, goto = [part.strip() for part in goto.split(_OPTION_CALL_MARKER, 1)]

            # parse key [;aliases|pattern]
            key = [part.strip() for part in key.split(_OPTION_ALIAS_MARKER)]
            if not key:
                # fall back to this being the Nth option
                key = [f"{inum + 1}"]
            main_key = key[0]

            if main_key.startswith(_OPTION_INPUT_MARKER):
                # if we have a pattern, build the arguments for _default later
                pattern = main_key[len(_OPTION_INPUT_MARKER):].strip()
                inputparsemap[pattern] = goto
                print(f"registering input goto {pattern} -> {goto}")
            else:
                # a regular goto string/callable target
                option = {
                    "key": key,
                    "goto": (_generated_goto_func, {
                        "goto": goto,
                        "current_nodename": nodename,
                        "goto_callables": goto_callables})
                }
                if desc:
                    option["desc"] = desc
                options.append(option)

        if inputparsemap:
            # if this exists we must create a _default entry too
            options.append({
                "key": "_default",
                "goto": (_generated_input_goto_func, {
                    "gotomap": inputparsemap,
                    "current_nodename": nodename,
                    "goto_callables": goto_callables
                })
            })

        return options

    def _parse(caller, menu_template, goto_callables):
        """
        Parse the menu string format into a node tree.
        """
        nodetree = {}
        splits = _RE_NODE.split(menu_template)
        splits = splits[1:] if splits else []

        # from evennia import set_trace;set_trace(term_size=(140,120))
        content_map = {}
        for node_ind in range(0, len(splits), 2):
            nodename, nodetxt = splits[node_ind], splits[node_ind + 1]
            text, *optiontxt = _RE_OPTIONS_SEP.split(nodetxt, maxsplit=2)
            options = _parse_options(nodename, optiontxt, goto_callables)
            content_map[nodename] = (text, options)
            nodetree[nodename] = _generated_node
        caller.db._generated_menu_contents = content_map

        return nodetree

    return _parse(caller, menu_template, goto_callables)


def template2menu(caller, menu_template, goto_callables=None,
                  startnode="start", startnode_input=None, persistent=False,
                  **kwargs):
    """
    Helper function to generate and start an EvMenu based on a menu template
    string.

    Args:
        caller (Object or Account): The entity using the menu.
        menu_template (str): The menu-template string describing the content
            and structure of the menu. It can also be the python-path to, or a module
            containing a `MENU_TEMPLATE` global variable with the template.
        goto_callables (dict, optional): Mapping of callable-names to
            module-global objects to reference by name in the menu-template.
            Must be on the form `callable(caller, raw_string, **kwargs)`.
        startnode (str, optional): The name of the startnode, if not 'start'.
        startnode_input (str or tuple, optional): If a string, the `raw_string`
            arg to pass into the starting node.  Otherwise should be on form
            `(raw_string, {kwargs})`, where `raw_string` and `**kwargs` will be
            passed into the start node.
        persistent (bool, optional): If the generated menu should be persistent.
        **kwargs: Other kwargs will be passed to EvMenu.


    """
    goto_callables = goto_callables or {}
    startnode_raw = ""
    startnode_kwargs = {"generated_nodename": startnode}
    if isinstance(startnode_input, str):
        startnode_raw = startnode_input
    elif isinstance(startnode_input, (tuple, list)):
        startnode_raw = startnode_input[0]
        startnode_kwargs.update(startnode_input[1])

    menu_tree = parse_menu_template(caller, menu_template, goto_callables)
    EvMenu(caller, menu_tree,
           startnode_input=(startnode_raw, startnode_kwargs),
           persistent=True, **kwargs)


def gotonode3(caller, raw_string, **kwargs):
    print("in gotonode3", caller, raw_string, kwargs)
    return None

def foo(caller, raw_string, **kwargs):
    print("in foo", caller, raw_string, kwargs)
    return "node2"

def bar(caller, raw_string, **kwargs):
    print("in bar", caller, raw_string, kwargs)
    return "bar"


def test_generator(caller):

    MENU_TEMPLATE = \
    """
    # node start

    Neque ea alias perferendis molestiae eligendi. Debitis exercitationem
    exercitationem quas blanditiis quisquam officia ut. Fugit aut fugit enim quia
    non. Earum et excepturi animi ex esse accusantium et. Id adipisci eos enim
    ratione.

    ## options

    1: first option -> node1
    2: second option -> node2
    3: node3 -> gotonode3()
    next;n: node2
    top: start
    > foo*: foo()
    > bar*: bar(a=4, boo=groo)
    > [5,6]0+?: foo()
    > great: node2
    > fail: bar()

    # node node1

    Neque ea alias perferendis molestiae eligendi. Debitis exercitationem
    exercitationem quas blanditiis quisquam officia ut. Fugit aut fugit enim quia
    non. Earum et excepturi animi ex esse accusantium et. Id adipisci eos enim
    ratione.

    ## options

    back: start
    to node 2: node2
    run foo (rerun node): foo()
    >: return to go back -> start

    # node node2

    In node 2!

    ## options

    back: back to start -> start


    # node bar

    In node bar!

    ## options

    back: back to start -> start
    end: end

    # node end

    In node end!

    """

    callables = {"gotonode3": gotonode3, "foo": foo, "bar": bar}
    template2menu(caller, MENU_TEMPLATE, callables)


if __name__ == "__main__":
    test_generator("<GriatchCaller>")
