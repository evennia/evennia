# EvMenu

EvMenu is used for generate branching multi-choice menus. Each menu 'node' can
accepts specific options as input or free-form input. Depending what the player
chooses, they are forwarded to different nodes in the menu.

## Introduction

The `EvMenu` utility class is located in [evennia/utils/evmenu.py](evennia.utils.evmenu).
It allows for easily adding interactive menus to the game; for example to implement Character
creation, building commands or similar. Below is an example of offering NPC conversation choices:

### Examples

This section gives some examples of how menus work in-game. A menu is a state
(it's actually a custom cmdset) where menu-specific commands are made available
to you. An EvMenu is usually started from inside a command, but could also
just be put in a file and run with `py`.

This is how the example menu will look in-game:

```
Is your answer yes or no?
_________________________________________
[Y]es! - Answer yes.
[N]o! - Answer no.
[A]bort - Answer neither, and abort.
```

If you pick (for example) Y(es), you will see

```
You chose yes!

Thanks for your answer. Goodbye!
```

After which the menu will end (in this example at least - it could also continue
on to other questions and choices or even repeat the same node over and over!)

Here's the full EvMenu code for this example:

```python
from evennia.utils import evmenu

def _handle_answer(caller, raw_input, **kwargs):
    answer = kwargs.get("answer")
    caller.msg(f"You chose {answer}!")
    return "end"  # name of next node

def node_question(caller, raw_input, **kwargs):
    text = "Is your answer yes or no?"
    options = (
        {"key": ("[Y]es!", "yes", "y"),
         "desc": Answer yes.",
         "goto": _handle_answer, {"answer": "yes"}},
        {"key": ("[N]o!", "no", "n"),
         "desc": "Answer no.",
         "goto": _handle_answer, {"answer": "no"}},
        {"key": ("[A]bort", "abort", "a"),
         "desc": "Answer neither, and abort.",
         "goto": "end"}
    )
    return text, options

def node_end(caller, raw_input, **kwargs):
    text "Thanks for your answer. Goodbye!"
    return text, None  # empty options ends the menu

evmenu.EvMenu(caller, {"start": node_question, "end": node_end})

```

Note the call to `EvMenu` at the end; this immediately creates the menu for the
`caller`. It also assigns the two node-functions to menu node-names `start` and
`end`, which is what the menu then uses to reference the nodes.

Each node of the menu is a function that returns the text and a list of dicts
describing the choices you can make on that node.

Each option details what it should show (key/desc) as well as which node to go
to (goto) next. The "goto" should be the name of the next node to go (if `None`,
the same node will be rerun again).

Above, the `Abort` option gives the "end" node name just as a string whereas the
yes/no options instead uses the callable `_handle_answer` but pass different
arguments to it. `_handle_answer` then returns the name of the next node (this
allows you to perform actions when making a choice before you move on to the
next node the menu). Note that `_handle_answer` is _not_ a node in the menu,
it's just a helper function.

When choosing 'yes' (or 'no') what happens here is that `_handle_answer` gets
called and echoes your choice before directing to the "end" node, which exits
the menu (since it doesn't return any options).

You can also write menus using the [EvMenu templating language](#evmenu-templating-language). This
allows you to use a text string to generate simpler menus with less boiler
plate. Let's create exactly the same menu using the templating language:

```python
from evennia.utils import evmenu

def _handle_answer(caller, raw_input, **kwargs):
    answer = kwargs.get("answer")
    caller.msg(f"You chose {answer}!")
    return "end"  # name of next node

menu_template = """

## node start

Is your answer yes or no?

## options

[Y]es!;yes;y: Answer yes. -> handle_answer(answer=yes)
[N]o!;no;n: Answer no. -> handle_answer(answer=no)
[A]bort;abort;a: Answer neither, and abort. -> end

## node end

Thanks for your answer. Goodbye!

"""

evmenu.template2menu(caller, menu_template, {"handle_answer": _handle_answer})

```

As seen, the `_handle_answer` is the same, but the menu structure is
described in the `menu_template` string. The `template2menu` helper
uses the template-string and a mapping of callables (we must add
`_handle_answer` here) to build a full EvMenu for us.

Here's another menu example, where we can choose how to interact with an NPC:

```
The guard looks at you suspiciously.
"No one is supposed to be in here ..."
he says, a hand on his weapon.
_______________________________________________
 1. Try to bribe him [Cha + 10 gold]
 2. Convince him you work here [Int]
 3. Appeal to his vanity [Cha]
 4. Try to knock him out [Luck + Dex]
 5. Try to run away [Dex]
```

```python

def _skill_check(caller, raw_string, **kwargs):
    skills = kwargs.get("skills", [])
    gold = kwargs.get("gold", 0)

    # perform skill check here, decide if check passed or not
    # then decide which node-name to return based on
    # the result ...

    return next_node_name

def node_guard(caller, raw_string, **kwarg):
    text = (
        'The guard looks at you suspiciously.\n'
        '"No one is supposed to be in here ..."\n'
        'he says, a hand on his weapon.'
    options = (
        {"desc": "Try to bribe on [Cha + 10 gold]",
         "goto": (_skill_check, {"skills": ["Cha"], "gold": 10})},
        {"desc": "Convince him you work here [Int].",
         "goto": (_skill_check, {"skills": ["Int"]})},
        {"desc": "Appeal to his vanity [Cha]",
         "goto": (_skill_check, {"skills": ["Cha"]})},
        {"desc": "Try to knock him out [Luck + Dex]",
         "goto": (_skill_check, {"skills"" ["Luck", "Dex"]})},
        {"desc": "Try to run away [Dex]",
         "goto": (_skill_check, {"skills": ["Dex"]})}
    return text, options
    )

# EvMenu called below, with all the nodes ...

```

Note that by skipping the `key` of the options, we instead get an
(auto-generated) list of numbered options to choose from.

Here the `_skill_check` helper will check (roll your stats, exactly what this
means depends on your game) to decide if your approach succeeded. It may then
choose to point you to nodes that continue the conversation or maybe dump you
into combat!


## Launching the menu

Initializing the menu is done using a call to the `evennia.utils.evmenu.EvMenu` class. This is the
most common way to do so - from inside a [Command](./Commands.md):

```python
# in, for example gamedir/commands/command.py

from evennia.utils.evmenu import EvMenu

class CmdTestMenu(Command):

    key = "testcommand"

    def func(self):

	EvMenu(self.caller, "world.mymenu")

```

When running this command, the menu will start using the menu nodes loaded from
`mygame/world/mymenu.py`. See next section on how to define menu nodes.

The `EvMenu` has the following optional callsign:

```python
EvMenu(caller, menu_data,
       startnode="start",
       cmdset_mergetype="Replace", cmdset_priority=1,
       auto_quit=True, auto_look=True, auto_help=True,
       cmd_on_exit="look",
       persistent=False,
       startnode_input="",
       session=None,
       debug=False,
       **kwargs)

```

 - `caller` (Object or Account): is a reference to the object using the menu. This object will get a
   new [CmdSet](./Command-Sets.md) assigned to it, for handling the menu.
 - `menu_data` (str, module or dict): is a module or python path to a module where the global-level
   functions will each be considered to be a menu node. Their names in the module will be the names
   by which they are referred to in the module. Importantly, function names starting with an
underscore
   `_` will be ignored by the loader. Alternatively, this can be a direct mapping
`{"nodename":function, ...}`.
 - `startnode` (str): is the name of the menu-node to start the menu at. Changing this means that
   you can jump into a menu tree at different positions depending on circumstance and thus possibly
   re-use menu entries.
 - `cmdset_mergetype` (str): This is usually one of "Replace" or "Union" (see [CmdSets](Command-
Sets).
   The first means that the menu is exclusive - the user has no access to any other commands while
   in the menu. The Union mergetype means the menu co-exists with previous commands (and may
overload
   them, so be careful as to what to name your menu entries in this case).
 - `cmdset_priority` (int): The priority with which to merge in the menu cmdset. This allows for
   advanced usage.
 - `auto_quit`, `auto_look`, `auto_help` (bool): If either of these are `True`, the menu
   automatically makes a `quit`, `look` or `help` command available to the user. The main reason why
   you'd want to turn this off is if  you want to use the aliases "q", "l" or "h" for something in
your
   menu. Nevertheless, at least `quit` is highly recommend - if `False`, the menu *must* itself
supply
   an "exit node" (a node without any options), or the user will be stuck in the menu until the
server
   reloads (or eternally if the menu is `persistent`)!
 - `cmd_on_exit` (str): This command string will be executed right *after* the menu has closed down.
   From experience, it's useful to trigger a "look" command to make sure the user is aware of the
   change of state; but any command can be used. If set to `None`, no command will be triggered
after
   exiting the menu.
 - `persistent` (bool) - if `True`, the menu will survive a reload (so the user will not be kicked
   out by the reload - make sure they can exit on their own!)
 - `startnode_input` (str or (str, dict) tuple): Pass an input text or a input text + kwargs to the
   start node as if it was entered on a fictional previous node. This can be very useful in order to
   start a menu differently depending on the Command's arguments in which it was initialized.
 - `session` (Session): Useful when calling the menu from an [Account](./Accounts.md) in
   `MULTISESSION_MODE` higher than 2, to make sure only the right Session sees the menu output.
 - `debug` (bool): If set, the `menudebug` command will be made available in the menu. Use it to
   list the current state of the menu and use `menudebug <variable>` to inspect a specific state
   variable from the list.
 - All other keyword arguments will be available as initial data for the nodes. They will be
   available in all nodes as properties on `caller.ndb._evmenu` (see below). These will also
survive a `@reload` if the menu is `persistent`.

You don't need to store the EvMenu instance anywhere - the very act of initializing it will store it
as `caller.ndb._evmenu` on the `caller`. This object will be deleted automatically when the menu
is exited and you can also use it to store your own temporary variables for access throughout the
menu. Temporary variables you store on a persistent `_evmenu` as it runs will
*not* survive a `@reload`, only those you set as part of the original `EvMenu` call.


## The Menu nodes

The EvMenu nodes consist of functions on one of these forms.

```python
def menunodename1(caller):
    # code
    return text, options

def menunodename2(caller, raw_string):
    # code
    return text, options

def menunodename3(caller, raw_string, **kwargs):
    # code
    return text, options

```

> While all of the above forms are okay, it's recommended to stick to the third and last form since
it
> gives the most flexibility. The previous forms are mainly there for backwards compatibility with
> existing menus from a time when EvMenu was less able.


### Input arguments to the node

 - `caller` (Object or Account): The object using the menu - usually a Character but could also be a
   Session or Account depending on where the menu is used.
 - `raw_string` (str): If this is given, it will be set to the exact text the user entered on the
   *previous* node (that is, the command entered to get to this node). On the starting-node of the
   menu, this will be an empty string, unless `startnode_input` was set.
 - `kwargs` (dict): These extra keyword arguments are extra optional arguments passed to the node
   when the user makes a choice on the *previous* node. This may include things like status flags
   and details about which exact option was chosen (which can be impossible to determine from
   `raw_string` alone). Just what is passed in `kwargs` is up to you when you create the previous
   node.

### Return values from the node

Each function must return two variables, `text` and `options`.


#### text

The `text` variable is a string or tuple. This text is what will be displayed when the user reaches
this node. If this is a tuple, then the first element of the tuple will be considered the displayed
text and the second the help-text to display when the user enters the `help` command on this node.

```python
    text = ("This is the text to display", "This is the help text for this node")
```

Returning a `None` text is allowed and simply leads to a node with no text and only options.  If the
help text is not given, the menu will give a generic error message when using `help`.


#### options

The `options` list describe all the choices available to the user when viewing this node. If
`options` is
returned as `None`, it means that this node is an *Exit node* - any text is displayed and then the
menu immediately exits, running the `exit_cmd` if given.

Otherwise, `options` should be a list (or tuple) of dictionaries, one for each option. If only one
option is
available, a single dictionary can also be returned. This is how it could look:


```python
def node_test(caller, raw_string, **kwargs):

    text = "A goblin attacks you!"

    options = (
	{"key": ("Attack", "a", "att"),
         "desc": "Strike the enemy with all your might",
         "goto": "node_attack"},
	{"key": ("Defend", "d", "def"),
         "desc": "Hold back and defend yourself",
         "goto": (_defend, {"str": 10, "enemyname": "Goblin"})})

    return text, options

```

This will produce a menu node looking like this:


```
A goblin attacks you!
________________________________

Attack: Strike the enemy with all your might
Defend: Hold back and defend yourself

```

##### option-key 'key'

The option's `key` is what the user should enter in order to choose that option. If given as a
tuple, the
first string of that tuple will be what is shown on-screen while the rest are aliases for picking
that option. In the above example, the user could enter "Attack" (or "attack", it's not
case-sensitive), "a" or "att" in order to attack the goblin. Aliasing is useful for adding custom
coloring to the choice. The first element of the aliasing tuple should then be the colored version,
followed by a version without color - since otherwise the user would have to enter the color codes
to select that choice.

Note that the `key` is *optional*. If no key is given, it will instead automatically be replaced
with a running number starting from `1`. If removing the `key` part of each option, the resulting
menu node would look like this instead:


```
A goblin attacks you!
________________________________

1: Strike the enemy with all your might
2: Hold back and defend yourself

```

Whether you want to use a key or rely on numbers is mostly
a matter of style and the type of menu.

EvMenu accepts one important special `key` given only as `"_default"`. This key is used when a user
enters something that does not match any other fixed keys. It is particularly useful for getting
user input:

```python
def node_readuser(caller, raw_string, **kwargs):
    text = "Please enter your name"

    options = {"key": "_default",
               "goto": "node_parse_input"}

    return text, options

```

A `"_default"` option does not show up in the menu, so the above will just be a node saying
`"Please enter your name"`. The name they entered will appear as `raw_string` in the next node.


#### option-key 'desc'

This simply contains the description as to what happens when selecting the menu option. For
`"_default"` options or if the `key` is already long or descriptive, it is not strictly needed. But
usually it's better to keep the `key` short and put more detail in `desc`.


#### option-key 'goto'

This is the operational part of the option and fires only when the user chooses said option. Here
are three ways to write it

```python

def _action_two(caller, raw_string, **kwargs):
    # do things ...
    return "calculated_node_to_go_to"

def _action_three(caller, raw_string, **kwargs):
    # do things ...
    return "node_four", {"mode": 4}

def node_select(caller, raw_string, **kwargs):

    text = ("select one",
            "help - they all do different things ...")

    options = ({"desc": "Option one",
		            "goto": "node_one"},
	             {"desc": "Option two",
		            "goto": _action_two},
	             {"desc": "Option three",
		            "goto": (_action_three, {"key": 1, "key2": 2})}
              )

    return text, options

```

As seen above, `goto` could just be pointing to a single `nodename` string - the name of the node to
go to. When given like this, EvMenu will look for a node named like this and call its associated
function as

```python
    nodename(caller, raw_string, **kwargs)
```

Here, `raw_string` is always the input the user entered to make that choice and `kwargs` are the
same as those `kwargs` that already entered the *current* node (they are passed on).

Alternatively the `goto` could point to a "goto-callable". Such callables are usually defined in the
same
module as the menu nodes and given names starting with `_` (to avoid being parsed as nodes
themselves). These callables will be called the same as a node function - `callable(caller,
raw_string, **kwargs)`, where `raw_string` is what the user entered on this node and `**kwargs` is
forwarded from the node's own input.

The `goto` option key could also point to a tuple `(callable, kwargs)` - this allows for customizing
the kwargs passed into the goto-callable, for example you could use the same callable but change the
kwargs passed into it depending on which option was actually chosen.

The "goto callable" must either return a string `"nodename"` or a tuple `("nodename", mykwargs)`.
This will lead to the next node being called as either `nodename(caller, raw_string, **kwargs)` or
`nodename(caller, raw_string, **mykwargs)` - so this allows changing (or replacing) the options
going
into the next node depending on what option was chosen.

There is one important case - if the goto-callable returns `None` for a `nodename`, *the current
node will run again*, possibly with different kwargs. This makes it very easy to re-use a node over
and over, for example allowing different options to update some text form being passed and
manipulated for every iteration.


> The EvMenu also supports the `exec` option key. This allows for running a callable *before* the
> goto-callable. This functionality comes from a time before goto could be a callable and is
> *deprecated* as of Evennia 0.8. Use `goto` for all functionality where you'd before use `exec`.


## Temporary storage

When the menu starts, the EvMenu instance is stored on the caller as `caller.ndb._evmenu`. Through
this object you can in principle reach the menu's internal state if you know what you are doing.
This is also a good place to store temporary, more global variables that may be cumbersome to keep
passing from node to node via the `**kwargs`. The `_evmnenu` will be deleted automatically when the
menu closes, meaning you don't need to worry about cleaning anything up.

If you want *permanent* state storage, it's instead better to use an Attribute on `caller`. Remember
that this will remain after the menu closes though, so you need to handle any needed cleanup
yourself.


## Customizing Menu formatting

The `EvMenu` display of nodes, options etc are controlled by a series of formatting methods on the
`EvMenu` class. To customize these, simply create a new child class of `EvMenu` and override as
needed. Here is an example:

```python
from evennia.utils.evmenu import EvMenu

class MyEvMenu(EvMenu):

    def nodetext_formatter(self, nodetext):
        """
        Format the node text itself.

        Args:
            nodetext (str): The full node text (the text describing the node).

        Returns:
            nodetext (str): The formatted node text.

        """

    def helptext_formatter(self, helptext):
        """
        Format the node's help text

        Args:
            helptext (str): The unformatted help text for the node.

        Returns:
            helptext (str): The formatted help text.

        """

    def options_formatter(self, optionlist):
        """
        Formats the option block.

        Args:
            optionlist (list): List of (key, description) tuples for every
                option related to this node.
            caller (Object, Account or None, optional): The caller of the node.

        Returns:
            options (str): The formatted option display.

        """

    def node_formatter(self, nodetext, optionstext):
        """
        Formats the entirety of the node.

        Args:
            nodetext (str): The node text as returned by `self.nodetext_formatter`.
            optionstext (str): The options display as returned by `self.options_formatter`.
            caller (Object, Account or None, optional): The caller of the node.

        Returns:
            node (str): The formatted node to display.

        """

```
See `evennia/utils/evmenu.py` for the details of their default implementations.

## EvMenu templating language

In evmenu.py are two helper functions `parse_menu_template` and `template2menu`
that is used to parse a _menu template_ string into an EvMenu:

    evmenu.template2menu(caller, menu_template, goto_callables)

One can also do it in two steps, by generate a menutree and using that to call
EvMenu normally:

    menutree = evmenu.parse_menu_template(caller, menu_template, goto_callables)
    EvMenu(caller, menutree)

With this latter solution, one could mix and match normally created menu nodes
with those generated by the template engine.

The `goto_callables` is a mapping `{"funcname": callable, ...}`, where each
callable must be a module-global function on the form
`funcname(caller, raw_string, **kwargs)` (like any goto-callable). The
`menu_template` is a multi-line string on the following form:

```python
menu_template = """

## node node1

Text for node

## options

key1: desc1 -> node2
key2: desc2 -> node3
key3: desc3 -> node4
"""
```

Each menu node is defined by a `## node <name>` containing the text of the node,
followed by `## options` Also `## NODE` and `## OPTIONS` work. No python code
logics is allowed in the template, this code is not evaluated but parsed. More
advanced dynamic usage requires a full node-function.

Except for defining the node/options, `#` act as comments - everything following
will be ignored by the template parser.

### Template Options

The option syntax is

    <key>: [desc ->] nodename or function-call

The 'desc' part is optional, and if that is not given, the `->` can be skipped
too:

    key: nodename

The key can both be strings and numbers. Separate the aliases with `;`.

    key: node1
    1: node2
    key;k: node3
    foobar;foo;bar;f;b: node4

Starting the key with the special letter `>` indicates that what follows is a
glob/regex matcher.

    >: node1          - matches empty input
    > foo*: node1     - everything starting with foo
    > *foo: node3     - everything ending with foo
    > [0-9]+?: node4  - regex (all numbers)
    > *: node5        - catches everything else (put as last option)

Here's how to call a goto-function from an option:

    key: desc -> myfunc(foo=bar)

For this to work `template2menu` or `parse_menu_template` must be given a dict
that includes `{"myfunc": _actual_myfunc_callable}`. All callables to be
available in the template must be mapped this way. Goto callables act like
normal EvMenu goto-callables and should have a callsign of
`_actual_myfunc_callable(caller, raw_string, **kwargs)` and return the next node
(passing dynamic kwargs into the next node does not work with the template
- use the full EvMenu if you want advanced dynamic data passing).

Only no or named keywords are allowed in these callables. So

    myfunc()         # OK
    myfunc(foo=bar)  # OK
    myfunc(foo)      # error!

This is because these properties are passed as `**kwargs` into the goto callable.

### Templating example

```python
from random import random
from evennia.utils import evmenu

def _gamble(caller, raw_string, **kwargs):

    caller.msg("You roll the dice ...")
    if random() < 0.5:
        return "loose"
    else:
        return "win"

def _try_again(caller, raw_string, **kwargs):
    return None   # reruns the same node

template_string = """

## node start

Death patiently holds out a set of bone dice to you.

"ROLL"

he says.

## options

1. Roll the dice -> gamble()
2. Try to talk yourself out of rolling -> ask_again()

## node win

The dice clatter over the stones.

"LOOKS LIKE YOU WIN THIS TIME"

says Death.

# (this ends the menu since there are no options)

## node loose

The dice clatter over the stones.

"YOUR LUCK RAN OUT"

says Death.

"YOU ARE COMING WITH ME."

# (this ends the menu, but what happens next - who knows!)

"""

goto_callables = {"gamble": _gamble, "ask_again": _ask_again}
evmenu.template2menu(caller, template_string, goto_callables)

```

## Examples:

- **[Simple branching menu](./EvMenu.md#example-simple-branching-menu)** - choose from options
- **[Dynamic goto](./EvMenu.md#example-dynamic-goto)** - jumping to different nodes based on response
- **[Set caller properties](./EvMenu.md#example-set-caller-properties)** - a menu that changes things
- **[Getting arbitrary input](./EvMenu.md#example-get-arbitrary-input)** - entering text
- **[Storing data between nodes](./EvMenu.md#example-storing-data-between-nodes)** - keeping states and
information while in the menu
- **[Repeating the same node](./EvMenu.md#example-repeating-the-same-node)** - validating within the node
before moving to the next
- **[Yes/No prompt](#example-yesno-prompt)** - entering text with limited possible responses
(this is *not* using EvMenu but the conceptually similar yet technically unrelated `get_input`
helper function accessed as `evennia.utils.evmenu.get_input`).


### Example: Simple branching menu

Below is an example of a simple branching menu node leading to different other nodes depending on
choice:

```python
# in mygame/world/mychargen.py

def define_character(caller):
    text = \
    """
    What aspect of your character do you want
    to change next?
    """
    options = ({"desc": "Change the name",
                "goto": "set_name"},
               {"desc": "Change the description",
                "goto": "set_description"})
    return text, options

EvMenu(caller, "world.mychargen", startnode="define_character")

```

This will result in the following node display:

```
What aspect of your character do you want
to change next?
_________________________
1: Change the name
2: Change the description
```

Note that since we didn't specify the "name" key, EvMenu will let the user enter numbers instead. In
the following examples we will not include the `EvMenu` call but just show nodes running inside the
menu. Also, since `EvMenu` also takes a dictionary to describe the menu, we could have called it
like this instead in the example:

```python
EvMenu(caller, {"define_character": define_character}, startnode="define_character")

```

### Example: Dynamic goto

```python

def _is_in_mage_guild(caller, raw_string, **kwargs):
    if caller.tags.get('mage', category="guild_member"):
        return "mage_guild_welcome"
    else:
        return "mage_guild_blocked"

def enter_guild:
    text = 'You say to the mage guard:'
    options ({'desc': 'I need to get in there.',
              'goto': _is_in_mage_guild},
             {'desc': 'Never mind',
              'goto': 'end_conversation'})
    return text, options
```

This simple callable goto will analyse what happens depending on who the `caller` is.  The
`enter_guild` node will give you a choice of what to say to the guard. If you try to enter, you will
end up in different nodes depending on (in this example) if you have the right [Tag](./Tags.md) set on
yourself or not. Note that since we don't include any 'key's in the option dictionary, you will just
get to pick between numbers.

### Example: Set caller properties

Here is an example of passing arguments into the `goto` callable and use that to influence
which node it should go to next:

```python

def _set_attribute(caller, raw_string, **kwargs):
    "Get which attribute to modify and set it"

    attrname, value = kwargs.get("attr", (None, None))
    next_node = kwargs.get("next_node")

    caller.attributes.add(attrname, attrvalue)

    return next_node


def node_background(caller):
    text = \
    f"""
    {caller.key} experienced a traumatic event
    in their childhood. What was it?
    """

    options = ({"key": "death",
                "desc": "A violent death in the family",
                "goto": (_set_attribute, {"attr": ("experienced_violence", True),
					  "next_node": "node_violent_background"})},
               {"key": "betrayal",
                "desc": "The betrayal of a trusted grown-up",
                "goto": (_set_attribute, {"attr": ("experienced_betrayal", True),
					  "next_node": "node_betrayal_background"})})
    return text, options
```

This will give the following output:

```
Kovash the magnificent experienced a traumatic event
in their childhood. What was it?
____________________________________________________
death: A violent death in the family
betrayal: The betrayal of a trusted grown-up

```

Note above how we use the `_set_attribute` helper function to set the attribute depending on the
User's choice. In thie case the helper function doesn't know anything about what node called it - we
even tell it which nodename it should return, so the choices leads to different paths in the menu.
We could also imagine the helper function analyzing what other choices


### Example: Get arbitrary input

An example of the menu asking the user for input - any input.

```python

def _set_name(caller, raw_string, **kwargs):

    inp = raw_string.strip()

    prev_entry = kwargs.get("prev_entry")

    if not inp:
        # a blank input either means OK or Abort
        if prev_entry:
            caller.key = prev_entry
            caller.msg(f"Set name to {prev_entry}.")
            return "node_background"
        else:
	    caller.msg("Aborted.")
	    return "node_exit"
    else:
        # re-run old node, but pass in the name given
        return None, {"prev_entry": inp}


def enter_name(caller, raw_string, **kwargs):

    # check if we already entered a name before
    prev_entry = kwargs.get("prev_entry")

    if prev_entry:
	text = "Current name: {}.\nEnter another name or <return> to accept."
    else:
	text = "Enter your character's name or <return> to abort."

    options = {"key": "_default",
               "goto": (_set_name, {"prev_entry": prev_entry})}

    return text, options

```

This will display as

```
Enter your character's name or <return> to abort.

> Gandalf

Current name: Gandalf
Enter another name or <return> to accept.

>

Set name to Gandalf.

```

Here we re-use the same node twice for reading the input data from the user. Whatever we enter will
be caught by the `_default` option and passed into the helper function. We also pass along whatever
name we have entered before. This allows us to react correctly on an "empty" input - continue to the
node named `"node_background"` if we accept the input or go to an exit node if we presses Return
without entering anything. By returning `None` from the helper function we automatically re-run the
previous node, but updating its ingoing kwargs to tell it to display a different text.



### Example: Storing data between nodes

A convenient way to store data is to store it on the `caller.ndb._evmenu` which you can reach from
every node. The advantage of doing this is that the `_evmenu` NAttribute will be deleted
automatically when you exit the menu.

```python

def _set_name(caller, raw_string, **kwargs):

    caller.ndb._evmenu.charactersheet = {}
    caller.ndb._evmenu.charactersheet['name'] = raw_string
    caller.msg(f"You set your name to {raw_string}")
    return "background"

def node_set_name(caller):
    text = 'Enter your name:'
    options = {'key': '_default',
               'goto': _set_name}

    return text, options

...


def node_view_sheet(caller):
    text = f"Character sheet:\n {self.ndb._evmenu.charactersheet}"

    options = ({"key": "Accept",
                "goto": "finish_chargen"},
	       {"key": "Decline",
                "goto": "start_over"})

    return text, options

```

Instead of passing the character sheet along from node to node through the `kwargs` we instead
set it up temporarily on `caller.ndb._evmenu.charactersheet`. This makes it easy to reach from
all nodes. At the end we look at it and, if we accept the character the menu will likely save the
result to permanent storage and exit.

> One point to remember though is that storage on `caller.ndb._evmenu` is not persistent across
> `@reloads`. If you are using a persistent menu (using `EvMenu(..., persistent=True)` you should
use
> `caller.db` to store in-menu data like this as well. You must then yourself make sure to clean it
> when the user exits the menu.


### Example: Repeating the same node

Sometimes you want to make a chain of menu nodes one after another, but you don't want the user to
be able to continue to the next node until you have verified that what they input in the previous
node is ok. A common example is a login menu:


```python

def _check_username(caller, raw_string, **kwargs):
    # we assume lookup_username() exists
    if not lookup_username(raw_string):
	# re-run current node by returning `None`
	caller.msg("|rUsername not found. Try again.")
	return None
    else:
	# username ok - continue to next node
	return "node_password"


def node_username(caller):
    text = "Please enter your user name."
    options = {"key": "_default",
               "goto": _check_username}
    return text, options


def _check_password(caller, raw_string, **kwargs):

    nattempts = kwargs.get("nattempts", 0)
    if nattempts > 3:
	caller.msg("Too many failed attempts. Logging out")
	return "node_abort"
    elif not validate_password(raw_string):
        caller.msg("Password error. Try again.")
	return None, {"nattempts", nattempts + 1}
    else:
	# password accepted
	return "node_login"

def node_password(caller, raw_string, **kwargs):
    text = "Enter your password."
    options = {"key": "_default",
	       "goto": _check_password}
    return text, options

```

This will display something like


```
---------------------------
Please enter your username.
---------------------------

> Fo

------------------------------
Username not found. Try again.
______________________________
abort: (back to start)
------------------------------

> Foo

---------------------------
Please enter your password.
---------------------------

> Bar

--------------------------
Password error. Try again.
--------------------------
```

And so on.

Here the goto-callables will return to the previous node if there is an error. In the case of
password attempts, this will tick up the `nattempts` argument that will get passed on from iteration
to iteration until too many attempts have been made.


### Defining nodes in a dictionary

You can also define your nodes directly in a dictionary to feed into the `EvMenu` creator.

```python
def mynode(caller):
   # a normal menu node function
   return text, options

menu_data = {"node1": mynode,
             "node2": lambda caller: (
                      "This is the node text",
                     ({"key": "lambda node 1",
                       "desc": "go to node 1 (mynode)",
                       "goto": "node1"},
                      {"key": "lambda node 2",
                       "desc": "go to thirdnode",
                       "goto": "node3"})),
             "node3": lambda caller, raw_string: (
                       # ... etc ) }

# start menu, assuming 'caller' is available from earlier
EvMenu(caller, menu_data, startnode="node1")

```

The keys of the dictionary become the node identifiers. You can use any callable on the right form
to describe each node. If you use Python `lambda` expressions you can make nodes really on the fly.
If you do, the lambda expression must accept one or two arguments and always return a tuple with two
elements (the text of the node and its options), same as any menu node function.

Creating menus like this is one way to present a menu that changes with the circumstances - you
could for example remove or add nodes before launching the menu depending on some criteria. The
drawback is that a `lambda` expression [is much more
limited](https://docs.python.org/2/tutorial/controlflow.html#lambda-expressions) than a full
function - for example you can't use other Python keywords like `if` inside the body of the
`lambda`.

Unless you are dealing with a relatively simple dynamic menu, defining menus with lambda's is
probably more work than it's worth: You can create dynamic menus by instead making each node
function more clever. See the [NPC shop tutorial](../Howtos/Tutorial-NPC-Merchants.md) for an example of this.


## Ask for simple input

This describes two ways for asking for simple questions from the user. Using Python's `input`
will *not* work in Evennia. `input` will *block* the entire server for *everyone* until that one
player has entered their text, which is not what you want.

### The `yield` way

In the `func` method of your Commands (only) you can use Python's built-in `yield` command to
request input in a similar way to `input`. It looks like this:

```python
result = yield("Please enter your answer:")
```

This will send "Please enter your answer" to the Command's `self.caller` and then pause at that
point. All other players at the server will be unaffected. Once caller enteres a reply, the code
execution will continue and you can do stuff with the `result`. Here is an example:

```python
from evennia import Command
class CmdTestInput(Command):
    key = "test"
    def func(self):
        result = yield("Please enter something:")
        self.caller.msg(f"You entered {result}.")
        result2 = yield("Now enter something else:")
        self.caller.msg(f"You now entered {result2}.")
```

Using `yield` is simple and intuitive, but it will only access input from `self.caller` and you
cannot abort or time out the pause until the player has responded. Under the hood, it is actually
just a wrapper calling `get_input` described in the following section.

> Important Note: In Python you *cannot mix `yield` and `return <value>` in the same method*. It has
> to do with `yield` turning the method into a
> [generator](https://www.learnpython.org/en/Generators). A `return` without an argument works, you
> can just not do `return <value>`. This is usually not something you need to do in `func()` anyway,
> but worth keeping in mind.

### The `get_input` way

The evmenu module offers a helper function named `get_input`. This is wrapped by the `yield`
statement which is often easier and more intuitive to use. But `get_input` offers more flexibility
and power if you need it. While in the same module as `EvMenu`, `get_input` is technically unrelated
to it. The `get_input` allows you to ask and receive simple one-line input from the user without
launching the full power of a menu to do so. To use, call `get_input` like this:

```python
get_input(caller, prompt, callback)
```

Here `caller` is the entity that should receive the prompt for input given as `prompt`. The
`callback` is a callable `function(caller, prompt, user_input)` that you define to handle the answer
from the user. When run, the caller will see `prompt` appear on their screens and *any* text they
enter will be sent into the callback for whatever processing you want.

Below is a fully explained callback and example call:

```python
from evennia import Command
from evennia.utils.evmenu import get_input

def callback(caller, prompt, user_input):
    """
    This is a callback you define yourself.

    Args:
        caller (Account or Object): The one being asked
          for input
        prompt (str): A copy of the current prompt
        user_input (str): The input from the account.

    Returns:
        repeat (bool): If not set or False, exit the
          input prompt and clean up. If returning anything
          True, stay in the prompt, which means this callback
          will be called again with the next user input.
    """
    caller.msg(f"When asked '{prompt}', you answered '{user_input}'.")

get_input(caller, "Write something! ", callback)
```

This will show as

```
Write something!
> Hello
When asked 'Write something!', you answered 'Hello'.

```

Normally, the `get_input` function quits after any input, but as seen in the example docs, you could
return True from the callback to repeat the prompt until you pass whatever check you want.

> Note: You *cannot* link consecutive questions by putting a new `get_input` call inside the
> callback If you want that you should use an EvMenu instead (see the [Repeating the same
> node](./EvMenu.md#example-repeating-the-same-node) example above). Otherwise you can either peek at the
> implementation of `get_input` and implement your own mechanism (it's just using cmdset nesting) or
> you can look at [this extension suggested on the mailing
> list](https://groups.google.com/forum/#!category-topic/evennia/evennia-questions/16pi0SfMO5U).


#### Example: Yes/No prompt

Below is an example of a Yes/No prompt using the `get_input` function:

```python
def yesno(caller, prompt, result):
    if result.lower() in ("y", "yes", "n", "no"):
        # do stuff to handle the yes/no answer
        # ...
        # if we return None/False the prompt state
        # will quit after this
    else:
        # the answer is not on the right yes/no form
        caller.msg("Please answer Yes or No. \n{prompt}")
@        # returning True will make sure the prompt state is not exited
        return True

# ask the question
get_input(caller, "Is Evennia great (Yes/No)?", yesno)
```

## The `@list_node` decorator

The `evennia.utils.evmenu.list_node` is an advanced decorator for use with `EvMenu` node functions.
It is used to quickly create menus for manipulating large numbers of items.


```
text here
______________________________________________

1. option1     7. option7      13. option13
2. option2     8. option8      14. option14
3. option3     9. option9      [p]revius page
4. option4    10. option10      page 2
5. option5    11. option11     [n]ext page
6. option6    12. option12

```

The menu will automatically create an multi-page option listing that one can flip through. One can
inpect each entry and then select them with prev/next. This is how it is used:


```python
from evennia.utils.evmenu import list_node


...

_options(caller):
    return ['option1', 'option2', ... 'option100']

_select(caller, menuchoice, available_choices):
    # analyze choice
    return "next_node"

@list_node(options, select=_select, pagesize=10)
def node_mylist(caller, raw_string, **kwargs):
    ...

    return text, options

```

The `options` argument to `list_node` is either a list, a generator or a callable returning a list
of strings for each option that should be displayed in the node.

The `select` is a callable in the example above but could also be the name of a menu node. If a
callable, the `menuchoice` argument holds the selection done and `available_choices` holds all the
options available. The callable should return the menu to go to depending on the selection (or
`None` to rerun the same node). If the name of a menu node, the selection will be passed as
`selection` kwarg to that node.

The decorated node itself should return `text` to display in the node. It must return at least an
empty dictionary for its options. It returning options, those will supplement the options
auto-created by the `list_node` decorator.


## Assorted notes

The EvMenu is implemented using [Commands](./Commands.md). When you start a new EvMenu, the user of the
menu will be assigned a [CmdSet](./Command-Sets.md) with the commands they need to navigate the menu.
This means that if you were to, from inside the menu, assign a new command set to the caller, *you
may override the Menu Cmdset and kill the menu*. If you want to assign cmdsets to the caller as part
of the menu, you should store the cmdset on `caller.ndb._evmenu` and wait to actually assign it
until the exit node.
