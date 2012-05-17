"""
Custom manager for Objects.
"""
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.fields import exceptions
from src.typeclasses.managers import TypedObjectManager
from src.typeclasses.managers import returns_typeclass, returns_typeclass_list
from src.utils import utils
from src.utils.utils import to_unicode

ObjAttribute = None

__all__ = ("ObjectManager",)

# Try to use a custom way to parse id-tagged multimatches.

_AT_MULTIMATCH_INPUT = utils.variable_from_module(*settings.SEARCH_AT_MULTIMATCH_INPUT.rsplit('.', 1))

class ObjectManager(TypedObjectManager):
    """
    This ObjectManager implementes methods for searching
    and manipulating Objects directly from the database.

    Evennia-specific search methods (will return Typeclasses or
    lists of Typeclasses, whereas Django-general methods will return
    Querysets or database objects).

    dbref (converter)
    dbref_search
    get_dbref_range
    object_totals
    typeclass_search
    get_object_with_user
    get_object_with_player
    get_objs_with_key_and_typeclass
    get_objs_with_attr
    get_objs_with_attr_match
    get_objs_with_db_property
    get_objs_with_db_property_match
    get_objs_with_key_or_alias
    get_contents
    object_search (interface to many of the above methods, equivalent to ev.search_object)
    copy_object

    """

    #
    # ObjectManager Get methods
    #

    # user/player related

    @returns_typeclass
    def get_object_with_user(self, user):
        """
        Matches objects with obj.player.user matching the argument.
        A player<->user is a one-to-relationship, so this always
        returns just one result or None.

        user - may be a user object or user id.
        """
        try:
            uid = int(user)
        except TypeError:
            try:
                uid = user.id
            except:
                return None
        try:
            return self.get(db_player__user__id=uid)
        except Exception:
            return None

    # This returns typeclass since get_object_with_user and get_dbref does.
    def get_object_with_player(self, search_string):
        """
        Search for an object based on its player's name or dbref.
        This search
        is sometimes initiated by appending a * to the beginning of
        the search criterion (e.g. in local_and_global_search).
        search_string:  (string) The name or dbref to search for.
        """
        search_string = to_unicode(search_string).lstrip('*')
        dbref = self.dbref(search_string)
        if not dbref:
            # not a dbref. Search by name.
            player_matches = User.objects.filter(username__iexact=search_string)
            if player_matches:
                dbref = player_matches[0].id
        # use the id to find the player
        return self.get_object_with_user(dbref)

    @returns_typeclass_list
    def get_objs_with_key_and_typeclass(self, oname, otypeclass_path):
        """
        Returns objects based on simultaneous key and typeclass match.
        """
        return self.filter(db_key__iexact=oname).filter(db_typeclass_path__exact=otypeclass_path)

    # attr/property related

    @returns_typeclass_list
    def get_objs_with_attr(self, attribute_name, location=None):
        """
        Returns all objects having the given attribute_name defined at all.
        """
        global _ObjAttribute
        if not ObjAttribute:
            from src.objects.models import ObjAttribute as _ObjAttribute
        lstring = ""
        if location:
            lstring = ", db_obj__db_location=location"
        attrs = eval("_ObjAttribute.objects.filter(db_key=attribute_name%s)" % lstring)
        return [attr.obj for attr in attrs]

    @returns_typeclass_list
    def get_objs_with_attr_match(self, attribute_name, attribute_value, location=None, exact=False):
        """
        Returns all objects having the valid
        attrname set to the given value. Note that no conversion is made
        to attribute_value, and so it can accept also non-strings.
        """
        global _ObjAttribute
        if not ObjAttribute:
            from src.objects.models import ObjAttribute as _ObjAttribute
        lstring = ""
        if location:
            lstring = ", db_obj__db_location=location"
        attrs = eval("ObjAttribute.objects.filter(db_key=attribute_name%s)" % lstring)
        # since attribute values are pickled in database, we cannot search directly, but
        # must loop through the results. .
        if exact:
            return [attr.obj for attr in attrs if attribute_value == attr.value]
        else:
            return [attr.obj for attr in attrs if to_unicode(attribute_value) in str(attr.value)]

    @returns_typeclass_list
    def get_objs_with_db_property(self, property_name, location=None):
        """
        Returns all objects having a given db field property.
        property_name = search string
        location - actual location object to restrict to

        """
        lstring = ""
        if location:
            lstring = ".filter(db_location=location)"
        try:
            return eval("self.exclude(db_%s=None)%s" % (property_name, lstring))
        except exceptions.FieldError:
            return []

    @returns_typeclass_list
    def get_objs_with_db_property_match(self, property_name, property_value, location, exact=False):
        """
        Returns all objects having a given db field property
        """
        lstring = ""
        if location:
            lstring = ", db_location=location"

        try:
            if exact:
                return eval("self.filter(db_%s__iexact=property_value%s)" % (property_name, lstring))
            else:
                return eval("self.filter(db_%s__icontains=property_value%s)" % (property_name, lstring))
        except exceptions.FieldError:
            return []

    @returns_typeclass_list
    def get_objs_with_key_or_alias(self, ostring, location, exact=False):
        """
        Returns objects based on key or alias match
        """
        lstring_key, lstring_alias, estring = "", "", "icontains"
        if location:
            lstring_key = ", db_location=location"
            lstring_alias = ", db_obj__db_location=location"
        if exact:
            estring = "__iexact"
        else:
            estring = "__istartswith"
        matches = eval("self.filter(db_key%s=ostring%s)" % (estring, lstring_key))
        if not matches:
            alias_matches = eval("self.model.alias_set.related.model.objects.filter(db_key%s=ostring%s)" % (estring, lstring_alias))
            matches = [alias.db_obj for alias in alias_matches]
        return matches

    # main search methods and helper functions

    @returns_typeclass_list
    def get_contents(self, location, excludeobj=None):
        """
        Get all objects that has a location
        set to this one.
        """
        estring = ""
        if excludeobj:
            estring = ".exclude(db_key=excludeobj)"
        return eval("self.filter(db_location__id=location.id)%s" % estring)

    @returns_typeclass_list
    def object_search(self, ostring, caller=None,
                      global_search=False,
                      attribute_name=None, location=None, single_result=False):
        """
        Search as an object and return results. The result is always an Object.
        If * is appended (player search, a Character controlled by this Player
        is looked for. The Character is returned, not the Player. Use player_search
        to find Player objects. Always returns a list.

        Arguments:
        ostring: (string) The string to compare names against.
                  Can be a dbref. If name is appended by *, a player is searched for.
        caller: (Object) The optional object performing the search.
        global_search (bool). Defaults to False. If a caller is defined, search will
                  be restricted to the contents of caller.location unless global_search
                  is True. If no caller is given (or the caller has no location), a
                  global search is assumed automatically.
        attribute_name: (string) Which object attribute to match ostring against. If not
                  set, the "key" and "aliases" properties are searched in order.
        location (Object): If set, this location's contents will be used to limit the search instead
                  of the callers. global_search will override this argument

        Returns:
        A list of matching objects (or a list with one unique match)

        """
        ostring = to_unicode(ostring, force_string=True)

        if not ostring:
            return []

        # Easiest case - dbref matching (always exact)
        dbref = self.dbref(ostring)
        if dbref:
            dbref_match = self.dbref_search(dbref)
            if dbref_match:
                return [dbref_match]

        if not location and caller and hasattr(caller, "location"):
            location = caller.location

        # Test some common self-references

        if location and ostring == 'here':
            return [location]
        if caller and ostring in ('me', 'self'):
            return [caller]
        if caller and ostring in ('*me', '*self'):
            return [caller]

        # Test if we are looking for an object controlled by a
        # specific player

        #logger.log_infomsg(str(type(ostring)))
        if ostring.startswith("*"):
            # Player search - try to find obj by its player's name
            player_match = self.get_object_with_player(ostring)
            if player_match is not None:
                return [player_match]

        # Search for keys, aliases or other attributes

        search_locations = [None] # this means a global search
        if not global_search and location:
            # Test if we are referring to the current room
            if location and (ostring.lower() == location.key.lower()
                             or ostring.lower() in [alias.lower() for alias in location.aliases]):
                return [location]
            # otherwise, setup the locations to search in
            search_locations = [location]
            if caller:
                search_locations.append(caller)

        def local_and_global_search(ostring, exact=False):
            "Helper method for searching objects"
            matches = []
            for location in search_locations:
                if attribute_name:
                    # Attribute/property search. First, search for db_<attrname> matches on the model
                    matches.extend(self.get_objs_with_db_property_match(attribute_name, ostring, location, exact))
                    if not matches:
                        # Next, try Attribute matches
                        matches.extend(self.get_objs_with_attr_match(attribute_name, ostring, location, exact))
                else:
                    # No attribute/property named. Do a normal key/alias-search
                    matches.extend(self.get_objs_with_key_or_alias(ostring, location, exact))
            return matches

        # Search through all possibilities.

        match_number = None
        matches = local_and_global_search(ostring, exact=True)
        if not matches:
            # if we have no match, check if we are dealing with an "N-keyword" query - if so, strip it.
            match_number, ostring = _AT_MULTIMATCH_INPUT(ostring)
            if match_number != None and ostring:
                # Run search again, without match number:
                matches = local_and_global_search(ostring, exact=True)
            if ostring and (len(matches) > 1 or not matches):
                # Already multimatch or no matches. Run a fuzzy matching.
                matches = local_and_global_search(ostring, exact=False)
        elif len(matches) > 1:
            # multiple matches already. Run a fuzzy search. This catches partial matches (suggestions)
            matches = local_and_global_search(ostring, exact=False)

        # deal with the result
        if len(matches) > 1 and match_number != None:
            # We have multiple matches, but a N-type match number is available to separate them.
            try:
                matches = [matches[match_number]]
            except IndexError:
                pass
        # We always have a (possibly empty) list at this point.
        return matches

    #
    # ObjectManager Copy method
    #

    def copy_object(self, original_object, new_key=None,
                    new_location=None, new_player=None, new_home=None,
                    new_permissions=None, new_locks=None, new_aliases=None, new_destination=None):
        """
        Create and return a new object as a copy of the original object. All will
        be identical to the original except for the arguments given specifically
        to this method.

        original_object (obj) - the object to make a copy from
        new_key (str) - name the copy differently from the original.
        new_location (obj) - if not None, change the location
        new_home (obj) - if not None, change the Home
        new_aliases (list of strings) - if not None, change object aliases.
        new_destination (obj) - if not None, change destination
        """

        # get all the object's stats
        typeclass_path = original_object.typeclass_path
        if not new_key:
            new_key = original_object.key
        if not new_location:
            new_location = original_object.location
        if not new_home:
            new_home = original_object.home
        if not new_player:
            new_player = original_object.player
        if not new_aliases:
            new_aliases = original_object.aliases
        if not new_locks:
            new_locks = original_object.db_lock_storage
        if not new_permissions:
            new_permissions = original_object.permissions
        if not new_destination:
            new_destination = original_object.destination

        # create new object
        from src.utils import create
        from src.scripts.models import ScriptDB
        new_object = create.create_object(typeclass_path, key=new_key, location=new_location,
                                          home=new_home, player=new_player, permissions=new_permissions,
                                          locks=new_locks, aliases=new_aliases, destination=new_destination)
        if not new_object:
            return None

        # copy over all attributes from old to new.
        for attr in original_object.get_all_attributes():
            new_object.set_attribute(attr.key, attr.value)

        # copy over all cmdsets, if any
        for icmdset, cmdset in enumerate(original_object.cmdset.all()):
            if icmdset == 0:
                new_object.cmdset.add_default(cmdset)
            else:
                new_object.cmdset.add(cmdset)

        # copy over all scripts, if any
        for script in original_object.scripts.all():
            ScriptDB.objects.copy_script(script, new_obj=new_object.dbobj)

        return new_object
