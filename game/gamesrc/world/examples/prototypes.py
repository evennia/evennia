"""
Example prototypes read by the @spawn command but is also easily
available to use from code. Each prototype should be a dictionary. Use
the same name as the variable to refer to other prototypes.

Possible keywords are:
    prototype - string pointing to parent prototype of this structure
    key - string, the main object identifier
    typeclass - string, if not set, will use settings.BASE_OBJECT_TYPECLASS
    location - this should be a valid object or #dbref
    home - valid object or #dbref
    destination - only valid for exits (object or dbref)

    permissions - string or list of permission strings
    locks - a lock-string
    aliases - string or list of strings

    ndb_<name> - value of a nattribute (ndb_ is stripped)
    any other keywords are interpreted as Attributes and their values.

See the @spawn command and src.utils.spawner for more info.

"""

from random import randint

NOBODY = {}

GOBLIN = {
 "key": "goblin grunt",
 "health": lambda: randint(20,30),
 "resists": ["cold", "poison"],
 "attacks": ["fists"],
 "weaknesses": ["fire", "light"]
 }

GOBLIN_WIZARD = {
 "prototype": "GOBLIN",
 "key": "goblin wizard",
 "spells": ["fire ball", "lighting bolt"]
 }

GOBLIN_ARCHER = {
 "prototype": "GOBLIN",
 "key": "goblin archer",
 "attacks": ["short bow"]
}

ARCHWIZARD = {
 "attacks": ["archwizard staff"],
}

GOBLIN_ARCHWIZARD = {
 "key": "goblin archwizard",
 "prototype" : ("GOBLIN_WIZARD", "ARCHWIZARD")
}
