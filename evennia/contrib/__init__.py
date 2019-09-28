# -*- coding: utf-8 -*-
"""
This sub-package holds Evennia's contributions - code that may be
useful but are deemed too game-specific to go into the core library.

See README.md for more info.
"""
# imports for apidoc / turned off, due to typeclass-clashes; if imported
# like this; Django finds these typeclasses and makes for example Weapon
# unavailable to the user to add (since it exists in tutorialworld). We might
# need to change all names of contrib typeclasses (name them e.g. ContribTutorialWeapon
# or something); For now, we can un-comment this block ONLY for creating apidocs,
# but even so, you will get clashes when both using the tutorialworld and your
# own code, so somthing needs to be done here. See issue #766. /Griatch

# import evennia
# evennia._init()
# import barter, dice, extended_room, menu_login, talking_npc
# import chargen, email_login, gendersub, menusystem, slow_exit
# import tutorial_world, tutorial_examples
