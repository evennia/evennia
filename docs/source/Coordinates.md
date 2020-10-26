# Coordinates

# Adding room coordinates in your game

This tutorial is moderately difficult in content.  You might want to be familiar and at ease with
some Python concepts (like properties) and possibly Django concepts (like queries), although this
tutorial will try to walk you through the process and give enough explanations each time.  If you
don't feel very confident with math, don't hesitate to pause, go to the example section, which shows
a tiny map, and try to walk around the code or read the explanation.

Evennia doesn't have a coordinate system by default.  Rooms and other objects are linked by location
and content:

- An object can be in a location, that is, another object.  Like an exit in a room.
- An object can access its content.  A room can see what objects uses it as location (that would
  include exits, rooms, characters and so on).

This system allows for a lot of flexibility and, fortunately, can be extended by other systems.
Here, I offer you a way to add coordinates to every room in a way most compliant with Evennia
design.  This will also show you how to use coordinates, find rooms around a given point for
instance.

## Coordinates as tags

The first concept might be the most surprising at first glance: we will create coordinates as
[tags](./Tags).

> Why not attributes, wouldn't that be easier?

It would.  We could just do something like `room.db.x = 3`.  The advantage of using tags is that it
will be easy and effective to search.  Although this might not seem like a huge advantage right now,
with a database of thousands of rooms, it might make a difference, particularly if you have a lot of
things based on coordinates.

Rather than giving you a step-by-step process, I'll show you the code.  Notice that we use
properties to easily access and update coordinates.  This is a Pythonic approach.  Here's our first
`Room` class, that you can modify in `typeclasses/rooms.py`:

```python
# in typeclasses/rooms.py

from evennia import DefaultRoom

class Room(DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See examples/object.py for a list of
    properties and methods available on all Objects.
    """
    
    @property
    def x(self):
        """Return the X coordinate or None."""
        x = self.tags.get(category="coordx")
        return int(x) if isinstance(x, str) else None

    @x.setter
    def x(self, x):
        """Change the X coordinate."""
        old = self.tags.get(category="coordx")
        if old is not None:
            self.tags.remove(old, category="coordx")
        if x is not None:
            self.tags.add(str(x), category="coordx")

    @property
    def y(self):
        """Return the Y coordinate or None."""
        y = self.tags.get(category="coordy")
        return int(y) if isinstance(y, str) else None
    
    @y.setter
    def y(self, y):
        """Change the Y coordinate."""
        old = self.tags.get(category="coordy")
        if old is not None:
            self.tags.remove(old, category="coordy")
        if y is not None:
            self.tags.add(str(y), category="coordy")

    @property
    def z(self):
        """Return the Z coordinate or None."""
        z = self.tags.get(category="coordz")
        return int(z) if isinstance(z, str) else None
    
    @z.setter
    def z(self, z):
        """Change the Z coordinate."""
        old = self.tags.get(category="coordz")
        if old is not None:
            self.tags.remove(old, category="coordz")
        if z is not None:
            self.tags.add(str(z), category="coordz")
```

If you aren't familiar with the concept of properties in Python, I encourage you to read a good
tutorial on the subject.  [This article on Python properties](https://www.programiz.com/python-
programming/property)
is well-explained and should help you understand the idea.

Let's look at our properties for `x`.  First of all is the read property.

```python
    @property
    def x(self):
        """Return the X coordinate or None."""
        x = self.tags.get(category="coordx")
        return int(x) if isinstance(x, str) else None
```

What it does is pretty simple:

1. It gets the tag of category `"coordx"`.  It's the tag category where we store our X coordinate.
   The `tags.get` method will return `None` if the tag can't be found.
2. We convert the value to an integer, if it's a `str`.  Remember that tags can only contain `str`,
   so we'll need to convert it.

> I thought tags couldn't contain values?

Well, technically, they can't: they're either here or not.  But using tag categories, as we have
done, we get a tag, knowing only its category.  That's the basic approach to coordinates in this
tutorial.

Now, let's look at the method that will be called when we wish to set `x` in our room:

```python
    @x.setter
    def x(self, x):
        """Change the X coordinate."""
        old = self.tags.get(category="coordx")
        if old is not None:
            self.tags.remove(old, category="coordx")
        if x is not None:
            self.tags.add(str(x), category="coordx")
```

1. First, we remove the old X coordinate, if it exists.  Otherwise, we'd end up with two tags in our
   room with "coordx" as their category, which wouldn't do at all.
2. Then we add the new tag, giving it the proper category.

> Now what?

If you add this code and reload your game, once you're logged in with a character in a room as its
location, you can play around:

```
@py here.x
@py here.x = 0
@py here.y = 3
@py here.z = -2
@py here.z = None
```

The code might not be that easy to read, but you have to admit it's fairly easy to use.

## Some additional searches

Having coordinates is useful for several reasons:

1. It can help in shaping a truly logical world, in its geography, at least.
2. It can allow to look for specific rooms at given coordinates.
3. It can be good in order to quickly find the rooms around a location.
4. It can even be great in path-finding (finding the shortest path between two rooms).

So far, our coordinate system can help with 1., but not much else.  Here are some methods that we
could add to the `Room` typeclass.  These methods will just be search methods.  Notice that they are
class methods, since we want to get rooms.

### Finding one room

First, a simple one: how to find a room at a given coordinate?  Say, what is the room at X=0, Y=0,
Z=0?

```python
class Room(DefaultRoom):
    # ...
    @classmethod
    def get_room_at(cls, x, y, z):
        """
        Return the room at the given location or None if not found.

        Args:
            x (int): the X coord.
            y (int): the Y coord.
            z (int): the Z coord.

        Return:
            The room at this location (Room) or None if not found.

        """
        rooms = cls.objects.filter(
                db_tags__db_key=str(x), db_tags__db_category="coordx").filter(
                db_tags__db_key=str(y), db_tags__db_category="coordy").filter(
                db_tags__db_key=str(z), db_tags__db_category="coordz")
        if rooms:
            return rooms[0]

        return None
```

This solution includes a bit of [Django
queries](https://docs.djangoproject.com/en/1.11/topics/db/queries/).
Basically, what we do is reach for the object manager and search for objects with the matching tags.
Again, don't spend too much time worrying about the mechanism, the method is quite easy to use:

```
Room.get_room_at(5, 2, -3)
```

Notice that this is a class method: you will call it from `Room` (the class), not an instance.
Though you still can:

    @py here.get_room_at(3, 8, 0)

### Finding several rooms

Here's another useful method that allows us to look for rooms around a given coordinate.  This is
more advanced search and doing some calculation, beware!  Look at the following section if you're
lost.

```python
from math import sqrt

class Room(DefaultRoom):

    # ...

    @classmethod
    def get_rooms_around(cls, x, y, z, distance):
        """
        Return the list of rooms around the given coordinates.

        This method returns a list of tuples (distance, room) that
        can easily be browsed.  This list is sorted by distance (the
        closest room to the specified position is always at the top
        of the list).

        Args:
            x (int): the X coord.
            y (int): the Y coord.
            z (int): the Z coord.
            distance (int): the maximum distance to the specified position.

        Returns:
            A list of tuples containing the distance to the specified
            position and the room at this distance.  Several rooms
            can be at equal distance from the position.

        """
        # Performs a quick search to only get rooms in a square
        x_r = list(reversed([str(x - i) for i in range(0, distance + 1)]))
        x_r += [str(x + i) for i in range(1, distance + 1)]
        y_r = list(reversed([str(y - i) for i in range(0, distance + 1)]))
        y_r += [str(y + i) for i in range(1, distance + 1)]
        z_r = list(reversed([str(z - i) for i in range(0, distance + 1)]))
        z_r += [str(z + i) for i in range(1, distance + 1)]
        wide = cls.objects.filter(
                db_tags__db_key__in=x_r, db_tags__db_category="coordx").filter(
                db_tags__db_key__in=y_r, db_tags__db_category="coordy").filter(
                db_tags__db_key__in=z_r, db_tags__db_category="coordz")

        # We now need to filter down this list to find out whether
        # these rooms are really close enough, and at what distance
        # In short: we change the square to a circle.
        rooms = []
        for room in wide:
            x2 = int(room.tags.get(category="coordx"))
            y2 = int(room.tags.get(category="coordy"))
            z2 = int(room.tags.get(category="coordz"))
            distance_to_room = sqrt(
                    (x2 - x) ** 2 + (y2 - y) ** 2 + (z2 - z) ** 2)
            if distance_to_room <= distance:
                rooms.append((distance_to_room, room))

        # Finally sort the rooms by distance
        rooms.sort(key=lambda tup: tup[0])
        return rooms
```

This gets more serious.

1. We have specified coordinates as parameters.  We determine a broad range using the distance.
   That is, for each coordinate, we create a list of possible matches.  See the example below.
2. We then search for the rooms within this broader range.  It gives us a square
   around our location.  Some rooms are definitely outside the range.  Again, see the example below
to follow the logic.
3. We filter down the list and sort it by distance from the specified coordinates.

Notice that we only search starting at step 2.  Thus, the Django search doesn't look and cache all
objects, just a wider range than what would be really necessary.  This method returns a circle of
coordinates around a specified point.  Django looks for a square.  What wouldn't fit in the circle
is removed at step 3, which is the only part that includes systematic calculation.  This method is
optimized to be quick and efficient.

### An example

An example might help.  Consider this very simple map (a textual description follows):

```
4 A B C D
3 E F G H
2 I J K L
1 M N O P
  1 2 3 4
```

The X coordinates are given below.  The Y coordinates are given on the left.  This is a simple
square with 16 rooms: 4 on each line, 4 lines of them.  All the rooms are identified by letters in
this example: the first line at the top has rooms A to D, the second E to H, the third I to L and
the fourth M to P.  The bottom-left room, X=1 and Y=1, is M.  The upper-right room X=4 and Y=4 is D.

So let's say we want to find all the neighbors, distance 1, from the room J.  J is at X=2, Y=2.

So we use:

    Room.get_rooms_around(x=2, y=2, z=0, distance=1)
    # we'll assume a z coordinate of 0 for simplicity

1. First, this method gets all the rooms in a square around J.  So it gets E F G, I J K, M N O.  If
you want, draw the square around these coordinates to see what's happening.
2. Next, we browse over this list and check the real distance between J (X=2, Y=2) and the room.
The four corners of the square are not in this circle.  For instance, the distance between J and M
is not 1.  If you draw a circle of center J and radius 1, you'll notice that the four corners of our
square (E, G, M and O) are not in this circle. So we remove them.
3. We sort by distance from J.

So in the end we might obtain something like this:

```
[
    (0, J), # yes, J is part of this circle after all, with a distance of 0
    (1, F),
    (1, I),
    (1, K),
    (1, N),
]
```

You can try with more examples if you want to see this in action.

### To conclude

You can definitely use this system to map other objects, not just rooms.  You can easily remove the
`Z coordinate too, if you simply need X and Y.
