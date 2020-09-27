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

from evennia import EvMenu
from fnmatch import fnmatch

# support # NODE name, #NODE name ...
_RE_NODE = re.compile(r"#\s*?NODE\s+?(?P<nodename>\S+?)$", re.I + re.M)
_RE_OPTIONS_SEP = re.compile(r"##\s*?OPTIONS\s*?$", re.I + re.M)
_RE_CALLABLE = re.compile(r"\S+?\(\)", re.I + re.M)


def gotofunc(caller, raw_string, **kwargs):
    goto = kwargs['goto']
    callables = kwargs['callables']
    if _RE_CALLABLE.match(goto):
        gotofunc = goto.strip()[:-2]
        if gotofunc in callables:
            return callables[gotofunc](caller, raw_string, **kwargs)
    return goto

def inputgotofunc(caller, raw_string, **kwargs):
    gotomap = kwargs['gotomap']
    callables = kwargs['callables']

    # start with glob patterns
    for pattern, goto in gotomap.items():
        if fnmatch(raw_string.lower(), pattern):
            if _RE_CALLABLE.match(goto):
                gotofunc = goto.strip()[:-2]
                if gotofunc in callables:
                    return callables[gotofunc](caller, raw_string, **kwargs)
            return goto
    # no glob pattern match; try regex
    for pattern, goto in gotomap.items():
        if re.match(pattern, raw_string.lower(), flags=re.I + re.M):
            if _RE_CALLABLE.match(goto):
                gotofunc = goto.strip()[:-2]
                if gotofunc in callables:
                    return callables[gotofunc](caller, raw_string, **kwargs)
            return goto
    # no match, rerun current node
    return None


def generated_node(caller, raw_string, text="", options=None,
                   nodename="", **kwargs):
    return text, options


class ParseMenuForm:

    def __init__(self, caller, formstr, callables=None):
        self.caller = caller
        self.formstr = formstr
        self.callables = callables or {}
        self.menutree = self.parse(formstr)

    def _generate_node(self, nodename, text, options):
        """
        Generate a node from the parsed string
        """
        def node(caller, raw_string, nodename=nodename, **kwargs):
            return text, options
        return node

    def _parse_options(self, optiontxt):
        """
        Parse option section into option dict.
        """
        options = []
        optiontxt = optiontxt[0].strip() if optiontxt else ""
        optionlist = [optline.strip() for optline in optiontxt.split("\n")]
        inputparsemap = {}

        for inum, optline in enumerate(optionlist):
            if optline.startswith("#") or not ":" in optline:
                # skip comments or invalid syntax
                continue
            key = ""
            desc = ""
            pattern = None

            key, goto = [part.strip() for part in optline.split(":", 1)]

            # desc -> goto
            if "->" in goto:
                desc, goto = [part.strip() for part in goto.split("->", 1)]

            # parse key [pattern]
            key = [part.strip() for part in key.split(";")]
            if not key:
                # fall back to this being the Nth option
                key = [f"{inum + 1}"]
            main_key = key[0]

            if main_key.startswith(">input"):
                key[0] = "_default"
                pattern = main_key[6:].strip()

            if pattern is not None:
                # if we have a pattern, build the arguments for _default later
                inputparsemap[pattern] = goto
            else:
                # a regular goto string target
                option = {
                    "key": key,
                    "goto": (gotofunc, {
                        "goto": goto,
                        "callables": self.callables})
                }
                if desc:
                    option["desc"] = desc
                options.append(option)

        if inputparsemap:
            # if this exists we must create a _default entry too
            options.append({
                "key": "_default",
                "goto": (inputgotofunc, {
                    "gotomap": inputparsemap,
                    "callables": self.callables
                })
            })

        return options

    def parse(self, formstr):
        """
        Parse the menu string format into a node tree.
        """
        nodetree = {}
        errors = []
        splits = _RE_NODE.split(formstr)
        splits = splits[1:] if splits else []

        # from evennia import set_trace;set_trace(term_size=(140,120))

        for node_ind in range(0, len(splits), 2):
            nodename, nodetxt = splits[node_ind], splits[node_ind + 1]
            text, *optiontxt = _RE_OPTIONS_SEP.split(nodetxt, maxsplit=2)
            options = self._parse_options(optiontxt)
            nodetree[nodename] = self._generate_node(nodename, text, options)

        return nodetree


# class GameTutor(EvMenu):
#
#     # tutorial helpers
#
#     @staticmethod
#     def nextprev(prevnode, nextnode, **kwargs):
#         """
#         Add return to options to add a prev/next entry
#         """
#         if kwargs:
#             prevnode = (prevnode, kwargs)
#             nextnode = (nextnode, kwargs)
#
#         return (
#             {"key": ("|w[p]|nrev", "prev", "p"),
#              "goto": prevnode},
#             {"key": ("|w[n]|next", "next", "n"),
#              "goto": nextnode}
#         )


def test_generator(caller):

    MENU_DESC = \
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
    >input: return to go back -> start
    >input foo*: foo()
    >input bar*: bar()


    # node node1

    Neque ea alias perferendis molestiae eligendi. Debitis exercitationem
    exercitationem quas blanditiis quisquam officia ut. Fugit aut fugit enim quia
    non. Earum et excepturi animi ex esse accusantium et. Id adipisci eos enim
    ratione.

    ## options

    back: start
    to node 2: node2
    run foo (rerun node): foo()


    # node node2

    In node 2!

    ## options

    back: back to start -> start


    # node bar

    In node bar!

    ## options

    back: back to start -> start

    """

    def gotonode3(caller, raw_string, **kwargs):
        print("in gotonode3", caller, raw_string, kwargs)
        return None

    def foo(caller, raw_string, **kwargs):
        print("in foo", caller, raw_string, kwargs)
        return "node2"

    def bar(caller, raw_string, **kwargs):
        print("in bar", caller, raw_string, kwargs)
        return "bar"

    callables = {"gotonode3": gotonode3, "foo": foo, "bar": bar}

    mform = ParseMenuForm(caller, MENU_DESC, callables)

    if isinstance(caller, str):
        print(mform.menutree)
    else:
        EvMenu(caller, mform.menutree)


if __name__ == "__main__":
    test_generator("<GriatchCaller>")
