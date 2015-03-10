"""
Prototypes

A prototype is a simple way to create individualized instances of a
given `Typeclass`. For example, you might have a Sword typeclass that
implements everything a Sword would need to do. The only difference
between different individual Swords would be their key, description
and some Attributes. The Prototype system allows to create a range of
such Swords with only minor variations. Prototypes can also inherit
and combine together to form entire hierarchies (such as giving all
Sabres and all Broadswords some common properties). Note that bigger
variations, such as custom commands or functionality belong in a
hierarchy of typeclasses instead.

Example prototypes are read by the `@spawn` command but is also easily
available to use from code via `evennia.spawn` or `evennia.utils.spawner`.
Each prototype should be a dictionary. Use the same name as the
variable to refer to other prototypes.

Possible keywords are:
    prototype - string pointing to parent prototype of this structure.
    key - string, the main object identifier.
    typeclass - string, if not set, will use `settings.BASE_OBJECT_TYPECLASS`.
    location - this should be a valid object or #dbref.
    home - valid object or #dbref.
    destination - only valid for exits (object or dbref).

    permissions - string or list of permission strings.
    locks - a lock-string.
    aliases - string or list of strings.

    ndb_<name> - value of a nattribute (the "ndb_" part is ignored).
    any other keywords are interpreted as Attributes and their values.

See the `@spawn` command and `evennia.utils.spawner` for more info.

"""

#from random import randint
#
#NOBODY = {}
#
#GOBLIN = {
# "key": "goblin grunt",
# "health": lambda: randint(20,30),
# "resists": ["cold", "poison"],
# "attacks": ["fists"],
# "weaknesses": ["fire", "light"]
# }
#
#GOBLIN_WIZARD = {
# "prototype": "GOBLIN",
# "key": "goblin wizard",
# "spells": ["fire ball", "lighting bolt"]
# }
#
#GOBLIN_ARCHER = {
# "prototype": "GOBLIN",
# "key": "goblin archer",
# "attacks": ["short bow"]
#}
#
#ARCHWIZARD = {
# "attacks": ["archwizard staff"],
#}
#
#GOBLIN_ARCHWIZARD = {
# "key": "goblin archwizard",
# "prototype" : ("GOBLIN_WIZARD", "ARCHWIZARD")
#}
