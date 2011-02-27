"""
Custom manager for Objects.
"""
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.fields import exceptions 
from src.typeclasses.managers import TypedObjectManager
from src.typeclasses.managers import returns_typeclass, returns_typeclass_list

# Try to use a custom way to parse id-tagged multimatches.
IDPARSER_PATH = getattr(settings, 'ALTERNATE_OBJECT_SEARCH_MULTIMATCH_PARSER', 'src.objects.object_search_funcs')
if not IDPARSER_PATH:
    # can happen if variable is set to "" in settings
    IDPARSER_PATH = 'src.objects.object_search_funcs'
exec("from %s import object_multimatch_parser as IDPARSER" % IDPARSER_PATH)

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
    def get_objs_with_attr(self, attribute_name, location=None):
        """
        Returns all objects having the given attribute_name defined at all.
        """
        from src.objects.models import ObjAttribute
        lstring = ""
        if location:
            lstring = ", db_obj__db_location=location"        
        attrs = eval("ObjAttribute.objects.filter(db_key=attribute_name%s)" % lstring)
        return [attr.obj for attr in attrs]
    
    @returns_typeclass_list
    def get_objs_with_attr_match(self, attribute_name, attribute_value, location=None, exact=False):
        """
        Returns all objects having the valid 
        attrname set to the given value. Note that no conversion is made
        to attribute_value, and so it can accept also non-strings.
        """        
        from src.objects.models import ObjAttribute
        lstring = ""
        if location:
            lstring = ", db_obj__db_location=location"    
        attrs = eval("ObjAttribute.objects.filter(db_key=attribute_name%s)" % lstring)
        if exact:            
            return [attr.obj for attr in attrs if attribute_value == attr.value]
        else:
            return [attr.obj for attr in attrs if str(attribute_value) in str(attr.value)]
    
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
            estring = "iexact"
        matches = eval("self.filter(db_key__%s=ostring%s)" % (estring, lstring_key))        
        if not matches:
            alias_matches = eval("self.model.alias_set.related.model.objects.filter(db_key__%s=ostring%s)" % (estring, lstring_alias))
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
    def object_search(self, character, ostring,
                      global_search=False, 
                      attribute_name=None, location=None):
        """
        Search as an object and return results.
        
        character: (Object) The object performing the search.
        ostring: (string) The string to compare names against.
                  Can be a dbref. If name is appended by *, a player is searched for.         
        global_search: Search all objects, not just the current location/inventory
        attribute_name: (string) Which attribute to search in each object.
                                 If None, the default 'key' attribute is used.        
        location: If None, character.location will be used. 
        """
        #ostring = str(ostring).strip()

        if not ostring or not character:
            return None 

        if not location:
            location = character.location        

        # Easiest case - dbref matching (always exact)        
        dbref = self.dbref(ostring)
        if dbref:
            dbref_match = self.dbref_search(dbref)
            if dbref_match:
                return [dbref_match]

        # Test some common self-references

        if location and ostring == 'here':
            return [location]                        
        if character and ostring in ['me', 'self']:
            return [character]
        if character and ostring in ['*me', '*self']:            
            return [character.player]                    
        
        # Test if we are looking for a player object 

        if str(ostring).startswith("*"):
            # Player search - try to find obj by its player's name
            player_match = self.get_object_with_player(ostring)
            if player_match is not None:
                return [player_match.player]

        # Search for keys, aliases or other attributes
                   
        search_locations = [None] # this means a global search
        if not global_search and location:
            # Test if we are referring to the current room
            if location and (ostring.lower() == location.key.lower() 
                             or ostring.lower() in [alias.lower() for alias in location.aliases]):
                return [location]
            # otherwise, setup the locations to search in 
            search_locations = [character, location]

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
            match_number, ostring = IDPARSER(ostring)
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
        # This is always a list.
        return matches
            
    #
    # ObjectManager Copy method
    #

    def copy_object(self, original_object, new_name=None,
                    new_location=None, new_home=None, new_aliases=None):
        """
        Create and return a new object as a copy of the source object. All will
        be identical to the original except for the arguments given specifically 
        to this method.

        original_object (obj) - the object to make a copy from
        new_name (str) - name the copy differently from the original. 
        new_location (obj) - if not None, change the location
        new_home (obj) - if not None, change the Home
        new_aliases (list of strings) - if not None, change object aliases.
        """

        # get all the object's stats
        typeclass_path = original_object.typeclass_path
        if not new_name:            
            new_name = original_object.key
        if not new_location:
            new_location = original_object.location
        if not new_home:
            new_home = original_object.new_home
        if not new_aliases:
            new_aliases = original_object.aliases        
        
        # create new object 
        from src import create 
        new_object = create.create_object(new_name, typeclass_path, new_location,
                                        new_home, user=None, aliases=new_aliases)
        if not new_object:
            return None        

        for attr in original_object.attr():
            # copy over all attributes from old to new. 
            new_object.attr(attr.attr_name, attr.value)

        return new_object
