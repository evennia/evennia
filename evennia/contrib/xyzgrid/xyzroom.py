"""
XYZ-aware rooms and exits.

These are intended to be used with the XYZgrid - which interprets the `Z` 'coordinate' as
different (named) 2D XY  maps. But if not wanting to use the XYZgrid gridding, these can also be
used as stand-alone XYZ-coordinate-aware rooms.

"""

from django.db.models import Q
from evennia.objects.objects import DefaultRoom, DefaultExit
from evennia.objects.manager import ObjectManager

# name of all tag categories. Note that the Z-coordinate is
# the `map_name` of the XYZgrid
MAP_X_TAG_CATEGORY = "room_x_coordinate"
MAP_Y_TAG_CATEGORY = "room_y_coordinate"
MAP_Z_TAG_CATEGORY = "room_z_coordinate"

MAP_XDEST_TAG_CATEGORY = "exit_dest_x_coordinate"
MAP_YDEST_TAG_CATEGORY = "exit_dest_y_coordinate"
MAP_ZDEST_TAG_CATEGORY = "exit_dest_z_coordinate"


class XYZManager(ObjectManager):
    """
    This is accessed as `.objects` on the coordinate-aware typeclasses (`XYZRoom`, `XYZExit`). It
    has all the normal Object/Room manager methods (filter/get etc) but also special helpers for
    efficiently querying the room in the database based on XY coordinates.

    """
    def filter_xyz(self, xyz=('*', '*', '*'), **kwargs):
        """
        Filter queryset based on XYZ position on the grid. The Z-position is the name of the XYMap
        Set a coordinate to `'*'` to act as a wildcard (setting all coords to `*` will thus find
        *all* XYZ rooms). This will also find children of XYZRooms on the given coordinates.

        Kwargs:
            xyz (tuple, optional): A coordinate tuple (X, Y, Z) where each element is either
                an `int` or `str`. The character `'*'` acts as a wild card. Note that
                the `Z`-coordinate is the name of the map (case-sensitive) in the XYZgrid contrib.
            **kwargs: All other kwargs are passed on to the query.

        Returns:
            django.db.queryset.Queryset: A queryset that can be combined
            with further filtering.

        """
        x, y, z = xyz
        wildcard = '*'

        return (
            self
            .filter_family(**kwargs)
            .filter(
                Q() if x == wildcard
                else Q(db_tags__db_key=str(x), db_tags__db_category=MAP_X_TAG_CATEGORY))
            .filter(
                Q() if y == wildcard
                else Q(db_tags__db_key=str(y), db_tags__db_category=MAP_Y_TAG_CATEGORY))
            .filter(
                Q() if z == wildcard
                else Q(db_tags__db_key=str(z), db_tags__db_category=MAP_Z_TAG_CATEGORY))
        )

    def get_xyz(self, xyz=(0, 0, 'map'), **kwargs):
        """
        Always return a single matched entity directly. This accepts no `*`-wildcards.
        This will also find children of XYZRooms on the given coordinates.

        Kwargs:
            xyz (tuple): A coordinate tuple of `int` or `str` (not `'*'`, no wildcards are
                allowed in get).  The `Z`-coordinate acts as the name (case-sensitive) of the map in
                the XYZgrid contrib.
            **kwargs: All other kwargs are passed on to the query.

        Returns:
            XYRoom: A single room instance found at the combination of x, y and z given.

        Raises:
            DoesNotExist: If no matching query was found.
            MultipleObjectsReturned: If more than one match was found (which should not
                possible with a unique combination of x,y,z).

        """
        x, y, z = xyz

        # mimic get_family
        paths = [self.model.path] + [
            "%s.%s" % (cls.__module__, cls.__name__) for cls in self._get_subclasses(self.model)
        ]
        kwargs["db_typeclass_path__in"] = paths

        try:
            return (
                self
                .filter(db_tags__db_key=str(x), db_tags__db_category=MAP_X_TAG_CATEGORY)
                .filter(db_tags__db_key=str(y), db_tags__db_category=MAP_Y_TAG_CATEGORY)
                .filter(db_tags__db_key=str(z), db_tags__db_category=MAP_Z_TAG_CATEGORY)
                .get(**kwargs)
            )
        except self.model.DoesNotExist:
            inp = (f"xyz=({x},{y},{z}), " +
                   ",".join(f"{key}={val}" for key, val in kwargs.items()))
            raise self.model.DoesNotExist(f"{self.model.__name__} "
                                          f"matching query {inp} does not exist.")


class XYZExitManager(XYZManager):
    """
    Used by Exits.
    Manager that also allows searching for destinations based on XY coordinates.

    """

    def filter_xyz_exit(self, xyz=('*', '*', '*'),
                        xyz_destination=('*', '*', '*'), **kwargs):
        """
        Used by exits (objects with a source and -destination property).
        Find all exits out of a source or to a particular destination. This will also find
        children of XYZExit on the given coords..

        Kwargs:
            xyz (tuple, optional): A coordinate (X, Y, Z) for the source location. Each
                element is either an `int` or `str`. The character `'*'` is used as a wildcard -
                so setting all coordinates to the wildcard will return *all* XYZExits.
                the `Z`-coordinate is the name of the map (case-sensitive) in the XYZgrid contrib.
            xyz_destination (tuple, optional): Same as `xyz` but for the destination of the
                exit.
            **kwargs: All other kwargs are passed on to the query.

        Returns:
            django.db.queryset.Queryset: A queryset that can be combined
            with further filtering.

        Notes:
            Depending on what coordinates are set to `*`, this can be used to
            e.g. find all exits in a room, or leading to a room or even to rooms
            in a particular X/Y row/column.

            In the XYZgrid, `z_source != z_destination` means a _transit_ between different maps.

        """
        x, y, z = xyz
        xdest, ydest, zdest = xyz_destination
        wildcard = '*'

        return (
            self
            .filter_family(**kwargs)
            .filter(
                Q() if x == wildcard
                else Q(db_tags__db_key=str(x), db_tags__db_category=MAP_X_TAG_CATEGORY))
            .filter(
                Q() if y == wildcard
                else Q(db_tags__db_key=str(y), db_tags__db_category=MAP_Y_TAG_CATEGORY))
            .filter(
                Q() if z == wildcard
                else Q(db_tags__db_key=str(z), db_tags__db_category=MAP_Z_TAG_CATEGORY))
            .filter(
                Q() if xdest == wildcard
                else Q(db_tags__db_key=str(xdest), db_tags__db_category=MAP_XDEST_TAG_CATEGORY))
            .filter(
                Q() if ydest == wildcard
                else Q(db_tags__db_key=str(ydest), db_tags__db_category=MAP_YDEST_TAG_CATEGORY))
            .filter(
                Q() if zdest == wildcard
                else Q(db_tags__db_key=str(zdest), db_tags__db_category=MAP_ZDEST_TAG_CATEGORY))
        )

    def get_xyz_exit(self, xyz=(0, 0, 'map'), xyz_destination=(0, 0, 'map'), **kwargs):
        """
        Used by exits (objects with a source and -destination property). Get a single
        exit. All source/destination coordinates (as well as the map's name) are required.
        This will also find children of XYZExits on the given coords.

        Kwargs:
            xyz (tuple, optional): A coordinate (X, Y, Z) for the source location. Each
                element is either an `int` or `str` (not `*`, no wildcards are allowed for get).
                the `Z`-coordinate is the name of the map (case-sensitive) in the XYZgrid contrib.
            xyz_destination_coord (tuple, optional): Same as the `xyz` but for the destination of
                the exit.
            **kwargs: All other kwargs are passed on to the query.

        Returns:
            XYZExit: A single exit instance found at the combination of x, y and xgiven.

        Raises:
            DoesNotExist: If no matching query was found.
            MultipleObjectsReturned: If more than one match was found (which should not
                be possible with a unique combination of x,y,x).

        Notes:
            All coordinates are required.

        """
        x, y, z = xyz
        xdest, ydest, zdest = xyz_destination
        # mimic get_family
        paths = [self.model.path] + [
            "%s.%s" % (cls.__module__, cls.__name__) for cls in self._get_subclasses(self.model)
        ]
        kwargs["db_typeclass_path__in"] = paths

        try:
            return (
                self
                .filter(db_tags__db_key=str(z), db_tags__db_category=MAP_Z_TAG_CATEGORY)
                .filter(db_tags__db_key=str(x), db_tags__db_category=MAP_X_TAG_CATEGORY)
                .filter(db_tags__db_key=str(y), db_tags__db_category=MAP_Y_TAG_CATEGORY)
                .filter(db_tags__db_key=str(xdest), db_tags__db_category=MAP_XDEST_TAG_CATEGORY)
                .filter(db_tags__db_key=str(ydest), db_tags__db_category=MAP_YDEST_TAG_CATEGORY)
                .filter(db_tags__db_key=str(zdest), db_tags__db_category=MAP_ZDEST_TAG_CATEGORY)
                .get(**kwargs)
            )
        except self.model.DoesNotExist:
            inp = (f"xyz=({x},{y},{z}),xyz_destination=({xdest},{ydest},{zdest})," +
                   ",".join(f"{key}={val}" for key, val in kwargs.items()))
            raise self.model.DoesNotExist(f"{self.model.__name__} "
                                          f"matching query {inp} does not exist.")


class XYZRoom(DefaultRoom):
    """
    A game location aware of its XYZ-position.

    """

    # makes the `room.objects.filter_xymap` available
    objects = XYZManager()

    def __str__(self):
        return repr(self)

    def __repr__(self):
        x, y, z = self.xyz
        return f"<XYZRoom '{self.db_key}', XYZ=({x},{y},{z})>"

    @property
    def xyz(self):
        if not hasattr(self, "_xyz"):
            x = self.tags.get(category=MAP_X_TAG_CATEGORY, return_list=False)
            y = self.tags.get(category=MAP_Y_TAG_CATEGORY, return_list=False)
            z = self.tags.get(category=MAP_Z_TAG_CATEGORY, return_list=False)
            if x is None or y is None or z is None:
                # don't cache unfinished coordinate
                return (x, y, z)
            # cache result
            self._xyz = (x, y, z)
        return self._xyz

    @classmethod
    def create(cls, key, account=None, xyz=(0, 0, 'map'), **kwargs):
        """
        Creation method aware of XYZ coordinates.

        Args:
            key (str): New name of object to create.
            account (Account, optional): Any Account to tie to this entity (usually not used for
                rooms).
            xyz (tuple, optional): A 3D coordinate (X, Y, Z) for this room's location on a
                map grid. Each element can theoretically be either `int` or `str`, but for the
                XYZgrid, the X, Y are always integers while the `Z` coordinate is used for the
                map's name.
            **kwargs: Will be passed into the normal `DefaultRoom.create` method.

        Returns:
            room (Object): A newly created Room of the given typeclass.
            errors (list): A list of errors in string form, if any.

        Notes:
            The (X, Y, Z) coordinate must be unique across the game. If trying to create
            a room at a coordinate that already exists, an error will be returned.

        """
        try:
            x, y, z = xyz
        except ValueError:
            return None, [f"XYRroom.create got `xyz={xyz}` - needs a valid (X,Y,Z) "
                          "coordinate of ints/strings."]

        existing_query = cls.objects.filter_xyz(xyz=(x, y, z))
        if existing_query.exists():
            existing_room = existing_query.first()
            return None, [f"XYRoom XYZ=({x},{y},{z}) already exists "
                          f"(existing room is named '{existing_room.db_key}')!"]

        tags = (
            (str(x), MAP_X_TAG_CATEGORY),
            (str(y), MAP_Y_TAG_CATEGORY),
            (str(z), MAP_Z_TAG_CATEGORY),
        )

        return DefaultRoom.create(key, account=account, tags=tags, typeclass=cls, **kwargs)


class XYZExit(DefaultExit):
    """
    An exit that is aware of the XYZ coordinate system.

    """

    objects = XYZExitManager()

    def __str__(self):
        return repr(self)

    def __repr__(self):
        x, y, z = self.xyz
        xd, yd, zd = self.xyz_destination
        return f"<XYZExit '{self.db_key}', XYZ=({x},{y},{z})->({xd},{yd},{zd})>"

    @property
    def xyz(self):
        if not hasattr(self, "_xyz"):
            x = self.tags.get(category=MAP_X_TAG_CATEGORY, return_list=False)
            y = self.tags.get(category=MAP_Y_TAG_CATEGORY, return_list=False)
            z = self.tags.get(category=MAP_Z_TAG_CATEGORY, return_list=False)
            if x is None or y is None or z is None:
                # don't cache yet unfinished coordinate
                return (x, y, z)
            # cache result
            self._xyz = (x, y, z)
        return self._xyz

    @property
    def xyz_destination(self):
        if not hasattr(self, "_xyz_destination"):
            xd = self.tags.get(category=MAP_XDEST_TAG_CATEGORY, return_list=False)
            yd = self.tags.get(category=MAP_YDEST_TAG_CATEGORY, return_list=False)
            zd = self.tags.get(category=MAP_ZDEST_TAG_CATEGORY, return_list=False)
            if xd is None or yd is None or zd is None:
                # don't cache unfinished coordinate
                return (xd, yd, zd)
            # cache result
            self._xyz_destination = (xd, yd, zd)
        return self._xyz_destination

    @classmethod
    def create(cls, key, account=None, xyz=(0, 0, 'map'), xyz_destination=(0, 0, 'map'),
               location=None, destination=None, **kwargs):
        """
        Creation method aware of coordinates.

        Args:
            key (str): New name of object to create.
            account (Account, optional): Any Account to tie to this entity (unused for exits).
            xyz (tuple or None, optional): A 3D coordinate (X, Y, Z) for this room's location
                on a map grid.  Each element can theoretically be either `int` or `str`, but for the
                XYZgrid contrib, the X, Y are always integers while the `Z` coordinate is used for
                the map's name. Set to `None` if instead using a direct room reference with
                `location`.
            xyz_destination (tuple, optional): The XYZ coordinate of the place the exit
                leads to. Will be ignored if `destination` is given directly.
            location (Object, optional): If given, overrides `xyz` coordinate. This can be used
                to place this exit in any room, including non-XYRoom type rooms.
            destination (Object, optional): If given, overrides `xyz_destination`. This can
                be any room (including non-XYRooms) and is not checked for XYZ coordinates.
            **kwargs: Will be passed into the normal `DefaultRoom.create` method.

        Returns:
            tuple: A tuple `(exit, errors)`, where the errors is a list containing all found
                errors (in which case the returned exit will be `None`).

        """
        tags = []
        if location:
            source = location
        else:
            try:
                x, y, z = xyz
            except ValueError:
                return None, ["XYExit.create need either `xyz=(X,Y,Z)` coordinate or a `location`."]
            else:
                source = XYZRoom.objects.get_xyz(xyz=(x, y, z))
                tags.extend(((str(x), MAP_X_TAG_CATEGORY),
                             (str(y), MAP_Y_TAG_CATEGORY),
                             (str(z), MAP_Z_TAG_CATEGORY)))
        if destination:
            dest = destination
        else:
            try:
                xdest, ydest, zdest = xyz_destination
            except ValueError:
                return None, ["XYExit.create need either `xyz_destination=(X,Y,Z)` coordinate "
                              "or a `destination`."]
            else:
                dest = XYZRoom.objects.get_xyz(xyz=(xdest, ydest, zdest))
                tags.extend(((str(xdest), MAP_XDEST_TAG_CATEGORY),
                             (str(ydest), MAP_YDEST_TAG_CATEGORY),
                             (str(zdest), MAP_ZDEST_TAG_CATEGORY)))

        return DefaultExit.create(
            key, source, dest,
            account=account, tags=tags, typeclass=cls, **kwargs)
