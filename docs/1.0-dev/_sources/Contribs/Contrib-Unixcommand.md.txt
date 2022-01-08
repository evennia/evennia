# Unix-like Command style parent

Contribution by Vincent Le Geoff (vlgeoff), 2017

This module contains a command class with an alternate syntax parser implementing 
Unix-style command syntax in-game. This means `--options`, positional arguments 
and stuff like `-n 10`. It might not the best syntax for the average player
but can be really useful for builders when they need to have a single command do
many things with many options. It uses the `ArgumentParser` from Python's standard
library under the hood.

## Installation

To use, inherit `UnixCommand` from this module from your own commands. You need
to override two methods:

- The `init_parser` method, which adds options to the parser. Note that you
  should normally *not* override the normal `parse` method when inheriting from
  `UnixCommand`.
- The `func` method, called to execute the command once parsed (like any Command).

Here's a short example:

```python
from evennia.contrib.base_systems.unixcommand import UnixCommand


class CmdPlant(UnixCommand):

    '''
    Plant a tree or plant.

    This command is used to plant something in the room you are in.

    Examples:
      plant orange -a 8
      plant strawberry --hidden
      plant potato --hidden --age 5

    '''

    key = "plant"

    def init_parser(self):
        "Add the arguments to the parser."
        # 'self.parser' inherits `argparse.ArgumentParser`
        self.parser.add_argument("key",
                help="the key of the plant to be planted here")
        self.parser.add_argument("-a", "--age", type=int,
                default=1, help="the age of the plant to be planted")
        self.parser.add_argument("--hidden", action="store_true",
                help="should the newly-planted plant be hidden to players?")

    def func(self):
        "func is called only if the parser succeeded."
        # 'self.opts' contains the parsed options
        key = self.opts.key
        age = self.opts.age
        hidden = self.opts.hidden
        self.msg("Going to plant '{}', age={}, hidden={}.".format(
                key, age, hidden))
```

To see the full power of argparse and the types of supported options, visit
[the documentation of argparse](https://docs.python.org/2/library/argparse.html).


----

<small>This document page is generated from `evennia/contrib/base_systems/unixcommand/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
