# -------------------------------------------------------------
#
# test menu strucure and testing command
#
# -------------------------------------------------------------

import random


def _generate_goto(caller, **kwargs):
    return kwargs.get("name", "test_dynamic_node"), {"name": "replaced!"}


def test_start_node(caller):
    menu = caller.ndb._menutree
    text = """
    This is an example menu.

    If you enter anything except the valid options, your input will be
    recorded and you will be brought to a menu entry showing your
    input.

    Select options or use 'quit' to exit the menu.

    The menu was initialized with two variables: %s and %s.
    """ % (
        menu.testval,
        menu.testval2,
    )

    options = (
        {
            "key": ("|yS|net", "s"),
            "desc": "Set an attribute on yourself.",
            "exec": lambda caller: caller.attributes.add("menuattrtest", "Test value"),
            "goto": "test_set_node",
        },
        {
            "key": ("|yL|nook", "l"),
            "desc": "Look and see a custom message.",
            "goto": "test_look_node",
        },
        {"key": ("|yV|niew", "v"), "desc": "View your own name", "goto": "test_view_node"},
        {
            "key": ("|yD|nynamic", "d"),
            "desc": "Dynamic node",
            "goto": (_generate_goto, {"name": "test_dynamic_node"}),
        },
        {
            "key": ("|yQ|nuit", "quit", "q", "Q"),
            "desc": "Quit this menu example.",
            "goto": "test_end_node",
        },
        {"key": "_default", "goto": "test_displayinput_node"},
    )
    return text, options


def test_look_node(caller):
    text = "This is a custom look location!"
    options = {
        "key": ("|yL|nook", "l"),
        "desc": "Go back to the previous menu.",
        "goto": "test_start_node",
    }
    return text, options


def test_set_node(caller):
    text = (
        """
    The attribute 'menuattrtest' was set to

            |w%s|n

    (check it with examine after quitting the menu).

    This node's has only one option, and one of its key aliases is the
    string "_default", meaning it will catch any input, in this case
    to return to the main menu.  So you can e.g. press <return> to go
    back now.
    """
        % caller.db.menuattrtest,  # optional help text for this node
        """
    This is the help entry for this node. It is created by returning
    the node text as a tuple - the second string in that tuple will be
    used as the help text.
    """,
    )

    options = {"key": ("back (default)", "_default"), "goto": "test_start_node"}
    return text, options


def test_view_node(caller, **kwargs):
    text = (
        """
    Your name is |g%s|n!

    click |lclook|lthere|le to trigger a look command under MXP.
    This node's option has no explicit key (nor the "_default" key
    set), and so gets assigned a number automatically. You can infact
    -always- use numbers (1...N) to refer to listed options also if you
    don't see a string option key (try it!).
    """
        % caller.key
    )
    if kwargs.get("executed_from_dynamic_node", False):
        # we are calling this node as a exec, skip return values
        caller.msg("|gCalled from dynamic node:|n \n {}".format(text))
        return
    else:
        options = {"desc": "back to main", "goto": "test_start_node"}
        return text, options


def test_displayinput_node(caller, raw_string):
    text = (
        """
    You entered the text:

        "|w%s|n"

    ... which could now be handled or stored here in some way if this
    was not just an example.

    This node has an option with a single alias "_default", which
    makes it hidden from view. It catches all input (except the
    in-menu help/quit commands) and will, in this case, bring you back
    to the start node.
    """
        % raw_string.rstrip()
    )
    options = {"key": "_default", "goto": "test_start_node"}
    return text, options


def _test_call(caller, raw_input, **kwargs):
    mode = kwargs.get("mode", "exec")

    caller.msg(
        "\n|y'{}' |n_test_call|y function called with\n "
        'caller: |n{}\n |yraw_input: "|n{}|y" \n kwargs: |n{}\n'.format(
            mode, caller, raw_input.rstrip(), kwargs
        )
    )

    if mode == "exec":
        kwargs = {"random": random.random()}
        caller.msg("function modify kwargs to {}".format(kwargs))
    else:
        caller.msg("|ypassing function kwargs without modification.|n")

    return "test_dynamic_node", kwargs


def test_dynamic_node(caller, **kwargs):
    text = """
    This is a dynamic node with input:
        {}
    """.format(
        kwargs
    )
    options = (
        {
            "desc": "pass a new random number to this node",
            "goto": ("test_dynamic_node", {"random": random.random()}),
        },
        {
            "desc": "execute a func with kwargs",
            "exec": (_test_call, {"mode": "exec", "test_random": random.random()}),
        },
        {"desc": "dynamic_goto", "goto": (_test_call, {"mode": "goto", "goto_input": "test"})},
        {
            "desc": "exec test_view_node with kwargs",
            "exec": ("test_view_node", {"executed_from_dynamic_node": True}),
            "goto": "test_dynamic_node",
        },
        {"desc": "back to main", "goto": "test_start_node"},
    )

    return text, options


def test_end_node(caller):
    text = """
    This is the end of the menu and since it has no options the menu
    will exit here, followed by a call of the "look" command.
    """
    return text, None


# class CmdTestMenu(Command):
#     """
#     Test menu
#
#     Usage:
#       testmenu <menumodule>
#
#     Starts a demo menu from a menu node definition module.
#
#     """
#
#     key = "testmenu"
#
#     def func(self):
#
#         if not self.args:
#             self.caller.msg("Usage: testmenu menumodule")
#             return
#         # start menu
#         EvMenu(
#             self.caller,
#             self.args.strip(),
#             startnode="test_start_node",
#             persistent=True,
#             cmdset_mergetype="Replace",
#             testval="val",
#             testval2="val2",
#         )
#
