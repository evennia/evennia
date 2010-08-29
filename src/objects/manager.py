"""
Custom manager for Objects.
"""
from django.conf import settings
from django.contrib.auth.models import User
from src.typeclasses.managers import TypedObjectManager
from src.typeclasses.managers import returns_typeclass_list
from src.utils import create 

# Try to use a custom way to parse id-tagged multimatches.
try:
    IDPARSER = __import__(
        settings.ALTERNATE_OBJECT_SEARCH_MULTIMATCH_PARSER).object_multimatch_parser
except Exception:
    from src.objects.object_search_funcs import object_multimatch_parser as IDPARSER

#
# Helper function for the ObjectManger's search methods
#

def match_list(searchlist, ostring, exact_match=True,
               attribute_name=None):            
    """
    Helper function.
    does name/attribute matching through a list of objects.
    """
    ostring = ostring.lower()
    if attribute_name:
        #search an arbitrary attribute name for a value match. 
        if exact_match:
            return [prospect for prospect in searchlist
                    if (hasattr(prospect, attribute_name) and
                       ostring == str(getattr(prospect, attribute_name)).lower()) \
                    or (ostring == str(prospect.get_attribute(attribute_name)).lower())]
        else:                    
            return [prospect for prospect in searchlist
                    if (hasattr(prospect, attribute_name) and
                        ostring in str(getattr(prospect, attribute_name)).lower()) \
                    or (ostring in (str(p).lower() for p in prospect.get_attribute(attribute_name)))]
    else:
        #search the default "key" attribute

        if exact_match:
            return [prospect for prospect in searchlist
                    if ostring == str(prospect.key).lower()]
        else:
            return [prospect for prospect in searchlist
                    if ostring in str(prospect.key).lower()]

    
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
   
    @returns_typeclass_list
    def get_object_with_user(self, user):
        """
        Matches objects with obj.player.user matching the argument.
        Both an user object and a user id may be supplied. 
        """
        try:
            uid = int(user)
        except TypeError:
            uid = user.id        
        return self.filter(db_player__user__id=uid)
        
    # This returns typeclass since get_object_with_user and get_dbref does. 
    def player_name_search(self, search_string):
        """        
        Search for an object based on its player's name or dbref. 
        This search
        is sometimes initiated by appending a * to the beginning of
        the search criterion (e.g. in local_and_global_search). 
        search_string:  (string) The name or dbref to search for.
        """
        search_string = str(search_string).lstrip('*')
        
        dbref = self.dbref(search_string)
        if dbref: 
            # this is a valid dbref. Try to match it. 
            dbref_match = self.dbref_search(dbref)
            if dbref_match:
                return dbref_match

        # not a dbref. Search by name.
        player_matches = User.objects.filter(username__iexact=search_string)
        if player_matches:
            uid = player_matches[0].id
            return self.get_object_with_user(uid)
        return None

    @returns_typeclass_list
    def get_objs_with_attr_match(self, attribute_name, attribute_value):
        """
        Returns all objects having the valid 
        attrname set to the given value. Note that no conversion is made
        to attribute_value, and so it can accept also non-strings.
        """
        
        return [prospect for prospect in self.all()
                if attribute_value 
                and attribute_value == prospect.get_attribute(attribute_name)]
    
    @returns_typeclass_list
    def get_objs_with_attr(self, attribute_name):
        """
        Returns all objects having the given attribute_name defined at all.
        """
        return [prospect for prospect in self.all()
                if prospect.get_attribute(attribute_name)]

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
    def separable_search(self, ostring, searchlist=None,
                           attribute_name=None, exact_match=False):
        """
        Searches for a object hit for ostring.

        This version handles search criteria of the type N-keyword, this is used
        to differentiate several objects of the exact same name, e.g. 1-box, 2-box etc.      

        ostring:     (string) The string to match against.
        searchlist:  (List of Objects) The objects to perform name comparisons on.
                      if not given, will search the database normally. 
        attribute_name: (string) attribute name to search, if None, object key is used. 
        exact_match: (bool) 'exact' or 'fuzzy' matching.

        Note that the fuzzy matching gives precedence to exact matches; so if your
        search query matches an object in the list exactly, it will be the only result.
        This means that if the list contains [box,box11,box12], the search string 'box'
        will only match the first entry since it is exact. The search 'box1' will however
        match both box11 and box12 since neither is an exact match.

        This method always returns a list, also for a single result. 
        """

        def run_dbref_search(ostring):
            "dbref matching only"
            dbref = self.dbref(ostring)
            if searchlist:            
                results = [prospect for prospect in searchlist
                           if prospect.id == dbref]
            else:
                results = self.filter(id=dbref)
            return results 

        def run_full_search(ostring, searchlist, exact_match=False):
            "full matching"
            if searchlist: 
                results = match_list(searchlist, ostring,
                                     exact_match, attribute_name)
            elif attribute_name:
                results = match_list(self.all(), ostring,
                                     exact_match, attribute_name)
            elif exact_match:
                results = self.filter(db_key__iexact=ostring)
            else:
                results = self.filter(db_key__icontains=ostring)
            return results 

        # Easiest case - dbref matching (always exact)        
        if self.dbref(ostring):
            results = run_dbref_search(ostring)
            if results:
                return results 
            
        # Full search - this may return multiple matches.
        results = run_full_search(ostring, searchlist, exact_match)
                           
        # Deal with results of full search 
        match_number = None
        if not results:
            # if we have no match, check if we are dealing
            # with a "N-keyword" query, if so, strip it out.
            match_number, ostring = IDPARSER(ostring)
            if match_number != None and ostring:
                # Run the search again, without the match number                
                results = run_full_search(ostring, searchlist, exact_match)

        elif not exact_match:
            # we have results, but are using fuzzy matching; run
            # second sweep in results to catch eventual exact matches
            # (these are given precedence, so a search for 'ball' in
            # ['ball', 'ball2'] will correctly return the first ball
            # only).
            exact_results = run_full_search(ostring, results, True)
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
                                 If None, the default 'name' attribute is used.        
        """
        ostring = str(ostring).strip()
            
        if not ostring or not character:
            return None 

        dbref = self.dbref(ostring)
        if dbref: 
            # this is a valid dbref. If it matches, we return directly.
            dbref_match = self.dbref_search(dbref)
            if dbref_match:
                return [dbref_match]

        location = character.location        

        # If the search string is one of the following, return immediately with
        # the appropriate result.        
        if location and ostring == 'here':
            return [location]

        if character and ostring in ['me', 'self']:
            return [character]
        if character and ostring in ['*me', '*self']:            
            return [character.player]

        if ostring.startswith("*"):
            # Player search - search player base
            player_string = ostring.lstrip("*")  
            player_match = self.player_name_search(player_string)
            if player_match is not None:
                return [player_match]            

        if global_search or not location:
            # search all objects
            return self.separable_search(ostring, None,
                                         attribute_name)
                    
        # None of the above cases yielded a return, so we fall through to
        # location/contents searches. 
        matches = []
        local_objs = []        
        local_objs.extend(character.contents)
        local_objs.extend(location.contents)
        local_objs.append(location) #easy to forget! 
        if local_objs:
            # normal key/attribute search (typedobject_search is 
            # found in class parent)            
            matches = self.separable_search(ostring, local_objs,
                                            attribute_name, exact_match=False)        
            if not matches:
                # no match, try an alias search 
                matches = self.alias_list_search(ostring, local_objs)
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
