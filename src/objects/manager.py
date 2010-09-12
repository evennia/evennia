"""
Custom manager for Objects.
"""
from django.conf import settings
from django.contrib.auth.models import User
from src.typeclasses.managers import TypedObjectManager
from src.typeclasses.managers import returns_typeclass, returns_typeclass_list
from src.utils import create 

# Try to use a custom way to parse id-tagged multimatches.
try:
    IDPARSER = __import__(
        settings.ALTERNATE_OBJECT_SEARCH_MULTIMATCH_PARSER).object_multimatch_parser
except Exception:
    from src.objects.object_search_funcs import object_multimatch_parser as IDPARSER

#
# Helper functions for the ObjectManger's search methods
#

def match_list(searchlist, ostring, exact_match=True,
               attribute_name=None):            
    """
    Helper function.
    does name/attribute matching through a list of objects.
    """

    if not ostring:
        return []

    if not attribute_name:
        attribute_name = "key"

    if isinstance(ostring, basestring): 
        # strings are case-insensitive
        ostring = ostring.lower()        
        if exact_match:
            return [prospect for prospect in searchlist
                    if (hasattr(prospect, attribute_name) and 
                        ostring == str(getattr(prospect, attribute_name)).lower())
                        or (prospect.has_attribute(attribute_name) and 
                            ostring == str(prospect.get_attribute(attribute_name)).lower())]
        else:
            return [prospect for prospect in searchlist
                    if (hasattr(prospect, attribute_name) and 
                        ostring in str(getattr(prospect, attribute_name)).lower())
                    or (prospect.has_attribute(attribute_name) and 
                        ostring in str(prospect.get_attribute(attribute_name)).lower())]
    else:
        # If it's not a string, we don't convert to lowercase. This is also 
        # always treated as an exact match.
        return [prospect for prospect in searchlist
                if (hasattr(prospect, attribute_name) and 
                    ostring == getattr(prospect, attribute_name))
                or (prospect.has_attribute(attribute_name) 
                    and ostring == prospect.get_attribute(attribute_name))]
    

def separable_search(ostring, searchlist,
                     attribute_name='db_key', exact_match=False):
    """
    Searches a list for a object match to ostring or separator+keywords. 

    This version handles search criteria defined by IDPARSER. By default this
    is of the type N-keyword, used to differentiate several objects of the 
    exact same name, e.g. 1-box, 2-box etc.      

    ostring:     (string) The string to match against.
    searchlist:  (List of Objects) The objects to perform attribute comparisons on.
    attribute_name: (string) attribute name to search.
    exact_match: (bool) 'exact' or 'fuzzy' matching.

    Note that the fuzzy matching gives precedence to exact matches; so if your
    search query matches an object in the list exactly, it will be the only result.
    This means that if the list contains [box,box11,box12], the search string 'box'
    will only match the first entry since it is exact. The search 'box1' will however
    match both box11 and box12 since neither is an exact match.

    This method always returns a list, also for a single result. 
    """

    # Full search - this may return multiple matches.
    results = match_list(searchlist, ostring, exact_match, attribute_name)

    # Deal with results of search
    match_number = None
    if not results:
        # if we have no match, check if we are dealing
        # with a "N-keyword" query, if so, strip it out.
        match_number, ostring = IDPARSER(ostring)
        if match_number != None and ostring:
            # Run the search again, without the match number                
            results = match_list(searchlist, ostring, exact_match, attribute_name)
    elif not exact_match:
        # we have results, but are using fuzzy matching; run
        # second sweep in results to catch eventual exact matches
        # (these are given precedence, so a search for 'ball' in
        # ['ball', 'ball2'] will correctly return the first ball
        # only).
        exact_results = match_list(results, ostring, True, attribute_name)            
        if exact_results:
            results = exact_results

    if len(results) > 1 and match_number != None:
        # We have multiple matches, but a N-type match number
        # is available to separate them.
        try:
            results = [results[match_number]]
        except IndexError:
            pass
    # this is always a list.
    return results



class ObjectManager(TypedObjectManager):
    """
    This is the main ObjectManager for all in-game objects. It
    implements search functions specialized for objects of this
    type, such as searches based on user, contents or location. 

    See src.dbobjects.TypedObjectManager for more general
    search methods. 
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

        user - mayb be a user object or user id.
        """
        try:
            uid = int(user)
        except TypeError:
            uid = user.id             
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
        search_string = str(search_string).lstrip('*')        
        dbref = self.dbref(search_string)
        if not dbref:           
            # not a dbref. Search by name.
            player_matches = User.objects.filter(username__iexact=search_string)
            if player_matches:
                dbref = player_matches[0].id
        # use the id to find the player
        return self.get_object_with_user(dbref)
        

    # attr/property related

    @returns_typeclass_list
    def get_objs_with_attr(self, attribute_name):
        """
        Returns all objects having the given attribute_name defined at all.
        """
        from src.objects.models import ObjAttribute
        return [attr.obj for attr in ObjAttribute.objects.filter(db_key=attribute_name)]

    @returns_typeclass_list
    def get_objs_with_attr_match(self, attribute_name, attribute_value):
        """
        Returns all objects having the valid 
        attrname set to the given value. Note that no conversion is made
        to attribute_value, and so it can accept also non-strings.
        """        
        from src.objects.models import ObjAttribute
        return [attr.obj for attr in ObjAttribute.objects.filter(db_key=attribute_name)
                if attribute_value == attr.value]    
    
    @returns_typeclass_list
    def get_objs_with_db_property(self, property_name):
        """
        Returns all objects having a given db field property
        """
        return [prospect for prospect in self.all() 
                if hasattr(prospect, 'db_%s' % property_name) 
                or hasattr(prospect, property_name)]
        
    @returns_typeclass_list
    def get_objs_with_db_property_match(self, property_name, property_value):
        """
        Returns all objects having a given db field property
        """
        try:
            return eval("self.filter(db_%s=%s)" % (property_name, property_value))
        except Exception:
            return []

    # main search methods and helper functions
        
    @returns_typeclass_list
    def get_contents(self, location, excludeobj=None):
        """
        Get all objects that has a location
        set to this one.
        """
        oquery = self.filter(db_location__id=location.id)
        if excludeobj:
            oquery = oquery.exclude(db_key=excludeobj)
        return oquery

    @returns_typeclass_list
    def alias_list_search(self, ostring, objlist):
        """
        Search a list of objects by trying to match their aliases. 
        """
        matches = []
        for obj in (obj for obj in objlist
                    if hasattr(obj, 'aliases') and
                    ostring in obj.aliases):
            matches.append(obj)
        return matches
            
    @returns_typeclass_list
    def object_search(self, character, ostring,
                      global_search=False, 
                      attribute_name=None):
        """
        Search as an object and return results.
        
        character: (Object) The object performing the search.
        ostring: (string) The string to compare names against.
                  Can be a dbref. If name is appended by *, a player is searched for.         
        global_search: Search all objects, not just the current location/inventory
        attribute_name: (string) Which attribute to search in each object.
                                 If None, the default 'key' attribute is used.        
        """
        #ostring = str(ostring).strip()

        if not ostring or not character:
            return None 

        location = character.location        


        # Easiest case - dbref matching (always exact)        
        dbref = self.dbref(ostring)
        if dbref:
            dbref_match = self.dbref_search(dbref)
            if dbref_match:
                return [dbref_match]
            
        # not a dbref. Search by attribute/property.
 
        if not attribute_name:
            # If the search string is one of the following, return immediately with
            # the appropriate result.        
            if location and ostring == 'here':
                return [location]            
            if character and ostring in ['me', 'self']:
                return [character]
            if character and ostring in ['*me', '*self']:            
                return [character.player]

            attribute_name = 'key'
    
        if str(ostring).startswith("*"):
            # Player search - try to find obj by its player's name
            player_string = ostring.lstrip("*") 
            player_match = self.get_obj_with_player(player_string)
            if player_match is not None:
                return [player_match]
        
        # find suitable objects

        if global_search or not location:
            # search all objects in database 
            objlist = self.get_objs_with_db_property(attribute_name)
            if not objlist:
                objlist = self.get_objs_with_attr(attribute_name)
        else:
            # local search                        
            objlist = character.contents
            objlist.extend(location.contents)                
            objlist.append(location) #easy to forget! 
        if not objlist:
            return []

        # do the search on the found objects
        matches = separable_search(ostring, objlist,
                                   attribute_name, exact_match=False)        

        if not matches and attribute_name in ('key', 'name'):
            # No matches. If we tried to match a key/name field, we also try to 
            # see if an alias works better.
            matches = self.alias_list_search(ostring, objlist)

        return matches 

    #
    # ObjectManager Copy method
    #

    def copy_object(self, original_object, new_name=None,
                    new_location=None, new_home=None, aliases=None):
        """
        Create and return a new object as a copy of the source object. All will
        be identical to the original except for the dbref and the 'user' field
        which will be set to None.

        original_object (obj) - the object to make a copy from
        new_name (str) - name the copy differently from the original. 
        new_location (obj) - if None, we create the new object in the same place as the old one.
        """

        # get all the object's stats
        name = original_object.key
        if new_name:
            name = new_name
        typeclass_path = original_object.typeclass_path

        # create new object 
        from src import create 
        new_object = create.create_object(name, typeclass_path, new_location,
                                        new_home, user=None, aliases=None)
        if not new_object:
            return None        

        for attr in original_object.attr():
            # copy over all attributes from old to new. 
            new_object.attr(attr.attr_name, attr.value)

        return new_object


    #
    # ObjectManager User control
    #

    def user_swap_object(self, uid, new_obj_id, delete_old_obj=False):
        """
        This moves the user from one database object to another.
        The new object must already exist. 
        delete_old_obj (bool) - Delete the user's old dbobject. 

        This is different from ObjectDB.swap_type() since it actually
        swaps the database object the user is connected to, rather
        than change any typeclass on the same dbobject. This means
        that the old object (typeclass and all) can remain unchanged
        in-game except it is now not tied to any user. 

        Note that the new object will be unchanged, the only
        difference is that its 'user' property is set to the
        user. No other initializations are done here, such as
        setting the default cmdset - this has to be done
        separately when calling this method. 

        This method raises Exceptions instead of logging feedback
        since this is a method which might be very useful to embed in
        your own game implementation.

        Also note that this method don't check any permissions beyond
        making sure no other user is connected to the object before
        swapping. 
        """
        # get the objects.
        try:
            user = User.get(uid)
            new_obj = self.get(new_obj_id)
        except:
            raise Exception("OBJ_FIND_ERROR")

        # check so the new object is not already controlled.
        if new_obj.user:
            if new_obj.user == user:
                raise Exception("SELF_CONTROL_ERROR")
            else:
                raise Exception("CONTROL_ERROR")                
        # set user to new object. 
        new_obj.user = user 
        new_obj.save()
        # get old object, sets its user to None and/or delete it
        for old_obj in self.get_object_with_user(uid):
            if delete_old_obj:
                old_obj.delete()
            else:
                old_obj.user = None
                old_obj.save()
