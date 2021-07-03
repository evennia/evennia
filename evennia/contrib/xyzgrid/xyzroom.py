"""
XYZ-aware rooms and exits.

These are intended to be used with the XYZgrid - which interprets the `Z` 'coordinate' as
different (named) 2D XY  maps. But if not wanting to use the XYZgrid gridding, these can also be
used as stand-alone XYZ-coordinate-aware rooms.

"""

from django.db.models import Q
from evennia.objects.objects import DefaultRoom, DefaultExit
from evennia.objects.manager import ObjectManager
from evennia.utils.utils import inherits_from

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
    def filter_xyz(self, coord=(None, None, 'map'), **kwargs):
        """
        Filter queryset based on map as well as x- or y-coordinate, or both. The map-name is
        required but not the coordinates - if only one coordinate is given, multiple rooms may be
        returned from the same coordinate row/column. If both coordinates are omitted (set to
        `None`), then all rooms of a given map is returned.

        Kwargs:
            coord (tuple, optional): A tuple (X, Y, Z) where each element is either
                an `int`, `str` or `None`. `None` acts as a wild card. Note that
                the `Z`-coordinate is the name of the map (case-sensitive) in the XYZgrid contrib.
            **kwargs: All other kwargs are passed on to the query.

        Returns:
            django.db.queryset.Queryset: A queryset that can be combined
            with further filtering.

        """
        x, y, z = coord

        return self.filter_family(
            (Q() if x is None else Q(db_tags__db_key=str(x),
                                     db_tags__db_category=MAP_X_TAG_CATEGORY)),
            (Q() if y is None else Q(db_tags__db_key=str(y),
                                     db_tags__db_category=MAP_Y_TAG_CATEGORY)),
            (Q() if z is None else Q(db_tags__db_key=str(z),
                                     db_tags__db_category=MAP_Z_TAG_CATEGORY)),
            **kwargs
        )

    def get_xyz(self, coord=(0, 0, 'map'), **kwargs):
        """
        Always return a single matched entity directly.

        Kwargs:
            coord (tuple): A tuple of `int` or `str` (not `None`). The `Z`-coordinate
                acts as the name (case-sensitive) of the map in the XYZgrid contrib.
            **kwargs: All other kwargs are passed on to the query.

        Returns:
            XYRoom: A single room instance found at the combination of x, y and z given.

        Raises:
            DoesNotExist: If no matching query was found.
            MultipleObjectsReturned: If more than one match was found (which should not
                possible with a unique combination of x,y,z).

        """
        x, y, z = coord
        return self.get_family(
            Q(db_tags__db_key=str(x), db_tags__db_category=MAP_X_TAG_CATEGORY),
            Q(db_tags__db_key=str(y), db_tags__db_category=MAP_Y_TAG_CATEGORY),
            Q(db_tags__db_key=str(z), db_tags__db_category=MAP_Z_TAG_CATEGORY),
            **kwargs
        )


class XYZExitManager(XYZManager):
    """
    Used by Exits.
    Manager that also allows searching for destinations based on XY coordinates.

    """

    def filter_xyz_exit(self, coord=(None, None, 'map'),
                        destination_coord=(None, None, 'map'), **kwargs):
        """
        Used by exits (objects with a source and -destination property).
        Find all exits out of a source or to a particular destination.

        Kwargs:
            coord (tuple, optional): A tuple (X, Y, Z) for the source location. Each
                element is either an `int`, `str` or `None`. `None` acts as a wild card. Note that
                the `Z`-coordinate is the name of the map (case-sensitive) in the XYZgrid contrib.
            destination_coord (tuple, optional): Same as the `coord` but for the destination of the
                exit.
            **kwargs: All other kwargs are passed on to the query.

        Returns:
            django.db.queryset.Queryset: A queryset that can be combined
            with further filtering.

        Notes:
            Depending on what coordinates are set to `None`, this can be used to
            e.g. find all exits in a room, or leading to a room or even to rooms
            in a particular X/Y row/column.

            In the XYZgrid, `z != zdest` means a _transit_ between different maps.

        """
        x, y, z = coord
        xdest, ydest, zdest = destination_coord

        return self.filter_family(
            (Q() if x is None else Q(db_tags__db_key=str(x),
                                     db_tags__db_category=MAP_X_TAG_CATEGORY)),
            (Q() if y is None else Q(db_tags__db_key=str(y),
                                     db_tags__db_category=MAP_Y_TAG_CATEGORY)),
            (Q() if z is None else Q(db_tags__db_key=str(z),
                                     db_tags__db_category=MAP_Z_TAG_CATEGORY)),
            (Q() if xdest is None else Q(db_tags__db_key=str(xdest),
                                         db_tags__db_category=MAP_XDEST_TAG_CATEGORY)),
            (Q() if ydest is None else Q(db_tags__db_key=str(ydest),
                                         db_tags__db_category=MAP_YDEST_TAG_CATEGORY)),
            (Q() if zdest is None else Q(db_tags__db_key=str(zdest),
                                         db_tags__db_category=MAP_ZDEST_TAG_CATEGORY)),
        )

    def get_xyz_exit(self, coord=(0, 0, 'map'), destination_coord=(0, 0, 'map'), **kwargs):
        """
        Used by exits (objects with a source and -destination property). Get a single
        exit. All source/destination coordinates (as well as the map's name) are required.

        Kwargs:
            coord (tuple, optional): A tuple (X, Y, Z) for the source location. Each
                element is either an `int` or `str` (not `None`).
                the `Z`-coordinate is the name of the map (case-sensitive) in the XYZgrid contrib.
            destination_coord (tuple, optional): Same as the `coord` but for the destination of the
                exit.
            **kwargs: All other kwargs are passed on to the query.

        Returns:
            XYZExit: A single exit instance found at the combination of x, y and xgiven.

        Raises:
            DoesNotExist: If no matching query was found.
            MultipleObjectsReturned: If more than one match was found (which should not
                possible with a unique combination of x,y,x).

        Notes:
            All coordinates are required.

        """
        x, y, z = coord
        xdest, ydest, zdest = destination_coord

        return self.get_family(
            Q(db_tags__db_key=str(z), db_tags__db_category=MAP_Z_TAG_CATEGORY),
            Q(db_tags__db_key=str(x), db_tags__db_category=MAP_X_TAG_CATEGORY),
            Q(db_tags__db_key=str(y), db_tags__db_category=MAP_Y_TAG_CATEGORY),
            Q(db_tags__db_key=str(xdest), db_tags__db_category=MAP_XDEST_TAG_CATEGORY),
            Q(db_tags__db_key=str(ydest), db_tags__db_category=MAP_YDEST_TAG_CATEGORY),
            Q(db_tags__db_key=str(zdest), db_tags__db_category=MAP_ZDEST_TAG_CATEGORY),
            **kwargs
        )


class XYZRoom(DefaultRoom):
    """
    A game location aware of its XY-coordinate and map.

    """

    # makes the `room.objects.filter_xymap` available
    objects = XYZManager()

    def __str__(self):
        return repr(self)

    def __repr__(self):
        x, y, z = self.xyzcoords
        return f"<XYZRoom '{self.db_key}', XYZ=({x},{y},{z})>"

    @property
    def xyzcoords(self):
        if not hasattr(self, "_xyzcoords"):
            x = self.tags.get(category=MAP_X_TAG_CATEGORY, return_list=False)
            y = self.tags.get(category=MAP_Y_TAG_CATEGORY, return_list=False)
            z = self.tags.get(category=MAP_Z_TAG_CATEGORY, return_list=False)
            self._xyzcoords = (x, y, z)
        return self._xyzcoords

    @classmethod
    def create(cls, key, account=None, coord=(0, 0, 'map'), **kwargs):
        """
        Creation method aware of coordinates.

        Args:
            key (str): New name of object to create.
            account (Account, optional): Any Account to tie to this entity (usually not used for
                rooms).
            coords (tuple, optional): A 3D coordinate (X, Y, Z) for this room's location on a
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
            x, y, z = coord
        except ValueError:
            return None, [f"XYRroom.create got `coord={coord}` - needs a valid (X,Y,Z) "
                          "coordinate of ints/strings."]

        existing_query = cls.objects.filter_xyz(coord=(x, y, z))
        if existing_query.exists():
            existing_room = existing_query.first()
            return None, [f"XYRoom XYZ={coord} already exists "
                          f"(existing room is named '{existing_room.db_key}')!"]

        tags = (
            (str(x), MAP_X_TAG_CATEGORY),
            (str(y), MAP_Y_TAG_CATEGORY),
            (str(z), MAP_Z_TAG_CATEGORY),
        )

        return DefaultRoom.create(key, account=account, tags=tags, typeclass=cls, **kwargs)


class XYZExit(DefaultExit):
    """
    An exit that is aware of the XY coordinate system.

    """

    objects = XYZExitManager()

    def __str__(self):
        return repr(self)

    def __repr__(self):
        x, y, z = self.xyzcoords
        xd, yd, zd = self.xyzdestcoords
        return f"<XYZExit '{self.db_key}', XYZ=({x},{y},{z})->({xd},{yd},{zd})>"

    @property
    def xyzcoords(self):
        if not hasattr(self, "_xyzcoords"):
            x = self.tags.get(category=MAP_X_TAG_CATEGORY, return_list=False)
            y = self.tags.get(category=MAP_Y_TAG_CATEGORY, return_list=False)
            z = self.tags.get(category=MAP_Z_TAG_CATEGORY, return_list=False)
            self._xyzcoords = (x, y, z)
        return self._xyzcoords

    @property
    def xyzdestcoords(self):
        if not hasattr(self, "_xyzdestcoords"):
            xd = self.tags.get(category=MAP_XDEST_TAG_CATEGORY, return_list=False)
            yd = self.tags.get(category=MAP_YDEST_TAG_CATEGORY, return_list=False)
            zd = self.tags.get(category=MAP_ZDEST_TAG_CATEGORY, return_list=False)
            self._xyzdestcoords = (xd, yd, zd)
        return self._xyzdestcoords

    @classmethod
    def create(cls, key, account=None, coord=(0, 0, 'map'), destination_coord=(0, 0, 'map'),
               location=None, destination=None, **kwargs):
        """
        Creation method aware of coordinates.

        Args:
            key (str): New name of object to create.
            account (Account, optional): Any Account to tie to this entity (unused for exits).
            coords (tuple or None, optional): A 3D coordinate (X, Y, Z) for this room's location
                on a map grid.  Each element can theoretically be either `int` or `str`, but for the
                XYZgrid contrib, the X, Y are always integers while the `Z` coordinate is used for
                the map's name. Set to `None` if instead using a direct room reference with
                `location`.  destination_coord (tuple or None, optional): Works as `coords`, but for
                destination of
                the exit. Set to `None` if using the `destination` kwarg to point to room directly.
            destination_coord (tuple, optional): The XYZ coordinate of the place the exit
                leads to. Will be ignored if `destination` is given directly.
            location (Object, optional): Only used if `coord` is not given. This can be used
                to place this exit in any room, including non-XYRoom type rooms.
            destination (Object, optional): If given, overrides `destination_coord`. This can
                be any room (including non-XYRooms) and is not checked for XY coordinates.
            **kwargs: Will be passed into the normal `DefaultRoom.create` method.

        Returns:
            tuple: A tuple `(exit, errors)`, where the errors is a list containing all found
                errors (in which case the returned exit will be `None`).

        """
        tags = []
        try:
            x, y, z = coord
        except ValueError:
            if not location:
                return None, ["XYExit.create need either a `coord` or a `location`."]
            source = location
        else:
            print("rooms:", XYZRoom.objects.all().count(), XYZRoom.objects.all())
            print("exits:", XYZExit.objects.all().count(), XYZExit.objects.all())
            source = XYZRoom.objects.get_xyz(coord=(x, y, z))
            tags.extend(((str(x), MAP_X_TAG_CATEGORY),
                         (str(y), MAP_Y_TAG_CATEGORY),
                         (str(z), MAP_Z_TAG_CATEGORY)))
        if destination:
            dest = destination
        else:
            try:
                xdest, ydest, zdest = destination_coord
            except ValueError:
                if not destination:
                    return None, ["XYExit.create need either a `destination_coord` or "
                                  "a `destination`."]
                dest = destination
            else:
                dest = XYZRoom.objects.get_xyz(coord=(xdest, ydest, zdest))
                tags.extend(((str(xdest), MAP_XDEST_TAG_CATEGORY),
                             (str(ydest), MAP_YDEST_TAG_CATEGORY),
                             (str(zdest), MAP_ZDEST_TAG_CATEGORY)))

        return DefaultExit.create(
            key, source, dest, account=account,
            location=location, tags=tags, typeclass=cls, **kwargs)
