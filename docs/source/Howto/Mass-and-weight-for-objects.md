# Mass and weight for objects


An easy addition to add dynamic variety to your world objects is to give them some mass.  Why mass
and not weight? Weight varies in setting; for example things on the Moon weigh 1/6 as much.  On
Earth's surface and in most environments, no relative weight factor is needed.

In most settings, mass can be used as weight to spring a pressure plate trap or a floor giving way,
determine a character's burden weight for travel speed...   The total mass of an object can
contribute to the force of a weapon swing, or a speeding meteor to give it a potential striking
force.

#### Objects

Now that we have reasons for keeping track of object mass, let's look at the default object class
inside your mygame/typeclasses/objects.py and see how easy it is to total up mass from an object and
its contents.

```python
# inside your mygame/typeclasses/objects.py

class Object(DefaultObject):
# [...]
    def get_mass(self):
        mass = self.attributes.get('mass', 1) # Default objects have 1 unit mass.
        return mass + sum(obj.get_mass() for obj in self.contents)
```

Adding the `get_mass` definition to the objects you want to sum up the masses for is done with
Python's "sum" function which operates on all the contents, in this case by summing them to
return a total mass value.

If you only wanted specific object types to have mass or have the new object type in a different
module, see [[Adding-Object-Typeclass-Tutorial]] with its Heavy class object. You could set the
default for Heavy types to something much larger than 1 gram or whatever unit you want to use.  Any
non-default mass would be stored on the `mass` [[Attributes]] of the objects.


#### Characters and rooms

You can add a `get_mass` definition to characters and rooms, also.

If you were in a one metric-ton elevator with four other friends also wearing armor and carrying
gold bricks, you might wonder if this elevator's going to move, and how fast.

Assuming the unit is grams and the elevator itself weights 1,000 kilograms, it would already be
`@set elevator/mass=1000000`, we're `@set me/mass=85000` and our armor is `@set armor/mass=50000`.
We're each carrying 20 gold bars each `@set gold bar/mass=12400` then step into the elevator and see
the following message in the elevator's appearance: `Elevator weight and contents should not exceed
3 metric tons.` Are we safe?  Maybe not if you consider dynamic loading. But at rest:

```python
# Elevator object knows when it checks itself:
if self.get_mass() < 3000000:
    pass  # Elevator functions as normal.
else:
    pass  # Danger! Alarm sounds, cable snaps, elevator stops...
```

#### Inventory
Example of listing mass of items in your inventory:

```python
class CmdInventory(MuxCommand):
    """
    view inventory
    Usage:
      inventory
      inv
    Switches:
      /weight to display all available channels.
    Shows your inventory: carrying, wielding, wearing, obscuring.
    """

    key = "inventory"
    aliases = ["inv", "i"]
    locks = "cmd:all()"

    def func(self):
        "check inventory"
        items = self.caller.contents
        if not items:
            string = "You are not carrying anything."
        else:
            table = prettytable.PrettyTable(["name", "desc"])
            table.header = False
            table.border = False
            for item in items:
                second = item.get_mass() \
                        if "weight" in self.switches else item.db.desc
                table.add_row([
                    str(item.get_display_name(self.caller.sessions)),
                    second and second or "",
                ])
            string = f"|wYou are carrying:\n{table}"
        self.caller.msg(string)

```