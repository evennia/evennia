"""
Light contrib to group objects by name and display plural names.

Evennia contrib - Vincent Le Goff 2017

This contrib allows to group object names (in 'look' for instance)
using their singualr names.  You could have a display varying from:
    You see: a rock, a rock
To:
    You see: a rock X 2
You could even customize it to have:
    You see: 2 rocks

To install, you simply need to import and inherit from the `PluralNames`
mixin in your typeclasses.  Be sure to put it first in your inheritance
tree.  You could do it for all your typeclasses, or just your rooms for
instance.

```python
# Example with 'typeclasses/rooms.py'
from evennia import DefaultRoom

from evennia.contrib.plural import PluralNames

class Room(PluralNames, DefaultRoom):

    # ...
```

The `PluralNames` is a very light mixin that will override your
`return_apperance` hook.  You can, however, write your own `return_appearance`
hook and use the `group_objects` directly (see below for more information).

To change the way your objects will display plural names, you can
override the `get_plural_name` method (see the default implementation
below).  You can do so with all your typeclasses, if you don't like the default.

"""

def group_objects(objects, attrname="key"):
    """
    Return the grouped list of objects, using their singular names.

    Args:
        objects (list ob Object): list of objects to be grouped.
        attrname (str, optional): the name of the singular attribute.

    Returns:
        grouped (list): the same list of objects grouped by names.
        The list will contain tuples: the number (int),
        the object (Object) and the list of all objects of the same name.

    Notes:
        In the case of grouping (if an entry has more than 1 object),
        only one of these objects will be displayed for grouping.
        This is usually the expected behavior.

        Grouping will occur based on the `attrname` argument.  By
        default, the objects' `key` are used as singular names.  You
        can provide a different attribute names.  It could be linked
        to a property, or an Evennia attribute (just give it
        "db.<name of attribute>" as value).

    Example:
        >>> group(rock1, tree, rock2)
        [
            (2, <Rock 1>, [<Rock 1>, <Rock 2>]),
            (1, <Tree>, [<Tree>]),
        ]

    """
    numbers = []
    group_names = {}
    for obj in objects:
        # Try to get the `attrname` property
        if "." in attrname:
            name = obj
            for part in attrname.split("."):
                name = getattr(name, part)
        else:
            name = getattr(obj, attrname)

        matches = group_names.get(name, [])
        matches.append(obj)
        group_names[name] = matches

        # Add only if number is 1
        if len(matches) == 1:
            numbers.append((obj, name))

    # Create the grouped list of objects
    grouped = []
    for obj, name in numbers:
        matches = group_names.get(name, [])
        number = len(matches)
        grouped.append((number, obj, matches))

    return grouped

def _get_plural_name(obj, number, looker, matches):
    """Helper function to return the plural name of an object."""
    name = obj.key + " X " + str(number)
    # If looker is a builder, show the IDs
    if obj.locks.check_lockstring(looker, "perm(Builders)"):
        name += "(" + ", ".join("#{}".format(match.id) for match in matches) + ")"

    return name


class PluralNames(object):

    """
    Mix-in to group object names by plural.

    This mix-in will override the methods if used:
        return_appearance: to return grouped objects.
        get_plural_name: get the plural name for this object.

    It means you could change the rule of pluralization by overriding
    the `get_plural_name` method.  By default, it will just append
    ' X {number}' to the objects' name.

    """

    def return_appearance(self, looker):
        """
        This formats a description. It is the hook a 'look' command
        should call.

        Args:
            looker (Object): Object doing the looking.
        """
        if not looker:
            return ""
        # get and identify all objects
        visible = (con for con in self.contents if con != looker and
                   con.access(looker, "view"))
        exits, users, things = [], [], []
        for con in visible:
            key = con.get_display_name(looker)
            if con.destination:
                exits.append(key)
            elif con.has_player:
                users.append("|c%s|n" % key)
            else:
                things.append(con)
        # get description, build string
        string = "|c%s|n\n" % self.get_display_name(looker)
        desc = self.db.desc
        if desc:
            string += "%s" % desc
        if exits:
            string += "\n|wExits:|n " + ", ".join(exits)
        if users or things:
            grouped = group_objects(things)
            things = []
            for number, obj, matches in grouped:
                if number == 1:
                    name = obj.get_display_name(looker)
                else:
                    # Call `get_plural_name` on `obj` if exist
                    if hasattr(obj, "get_plural_name"):
                        name = obj.get_plural_name(number, looker, matches)
                    else:
                        name = _get_plural_name(obj, number, looker, matches)

                things.append(name)

            string += "\n|wYou see:|n " + ", ".join(users + things)
        return string

    def get_plural_name(self, number, looker, matches):
        """
        Return the plural name for self.  A plural name is displayed if
        there is more than one object of the same name.

        Artgs:
            number (int): the number of objects (> 1) of that name.
            looker (Object): the object looking.
            matches (list of Object): list of objects with the same name.

        Regurns:
            name (str): the plural name of self in this quantity.

        Note:
            The `matches` argument is provided to have the list of
            all objects (including self) sharing the same singular name.

        """
        return _get_plural_name(self, number, looker, matches)
