# Evennia Multidescer

Contrib - Griatch 2016

A "multidescer" is a concept from the MUSH world. It allows for
creating, managing and switching between multiple character
descriptions. This multidescer will not require any changes to the
Character class, rather it will use the `multidescs` Attribute (a
list) and create it if it does not exist.

This contrib also works well together with the rpsystem contrib (which
also adds the short descriptions and the `sdesc` command).

## Installation

Edit `mygame/commands/default_cmdsets.py` and add
`from evennia.contrib.game_systems.multidescer import CmdMultiDesc` to the top.

Next, look up the `at_cmdset_create` method of the `CharacterCmdSet`
class and add a line `self.add(CmdMultiDesc())` to the end
of it.

Reload the server and you should have the +desc command available (it
will replace the default `desc` command).


----

<small>This document page is generated from `evennia/contrib/game_systems/multidescer/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
