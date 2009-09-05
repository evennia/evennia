"""
Custom manager for Object objects.
"""
from datetime import datetime, timedelta

from django.db import models
from django.db import connection
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from src.config.models import ConfigValue
from src.objects.exceptions import ObjectNotExist
from src.objects.util import object as util_object
from src import defines_global
from src import logger
    
class ObjectManager(models.Manager):

    #
    # ObjectManager Get methods 
    #
    
    def num_total_players(self):
        """
        Returns the total number of registered players.
        """
        return User.objects.count()

    def get_connected_players(self):
        """
        Returns the a QuerySet containing the currently connected players.
        """
        return self.filter(nosave_flags__contains="CONNECTED")

    def get_recently_created_users(self, days=7):
        """
        Returns a QuerySet containing the player User accounts that have been
        connected within the last <days> days.
        """
        end_date = datetime.now()
        tdelta = timedelta(days)
        start_date = end_date - tdelta
        return User.objects.filter(date_joined__range=(start_date, end_date))

    def get_recently_connected_users(self, days=7):
        """
        Returns a QuerySet containing the player User accounts that have been
        connected within the last <days> days.
        """
        end_date = datetime.now()
        tdelta = timedelta(days)
        start_date = end_date - tdelta
        return User.objects.filter(last_login__range=(start_date, end_date)).order_by('-last_login')
            
    def get_user_from_email(self, uemail):
        """
        Returns a player's User object when given an email address.
        """
        return User.objects.filter(email__iexact=uemail)

    def get_object_from_dbref(self, dbref):
        """
        Returns an object when given a dbref.
        """
        try:
            return self.get(id=dbref)
        except self.model.DoesNotExist:
            raise ObjectNotExist(dbref)        

    def object_totals(self):
        """
        Returns a dictionary with database object totals.
        """
        dbtotals = {
            "objects": self.count(),
            "things": self.filter(type=defines_global.OTYPE_THING).count(),
            "exits": self.filter(type=defines_global.OTYPE_EXIT).count(),
            "rooms": self.filter(type=defines_global.OTYPE_ROOM).count(),
            "garbage": self.filter(type=defines_global.OTYPE_GARBAGE).count(),
            "players": self.filter(type=defines_global.OTYPE_PLAYER).count(),
        }
        return dbtotals

    def get_nextfree_dbnum(self):
        """
        Figure out what our next free database reference number is.
        
        If we need to recycle a GARBAGE object, return the object to recycle
        Otherwise, return the first free dbref.
        """
        # First we'll see if there's an object of type 6 (GARBAGE) that we
        # can recycle.
        nextfree = self.filter(type__exact=defines_global.OTYPE_GARBAGE)
        if nextfree:
            # We've got at least one garbage object to recycle.
            return nextfree[0]
        else:
            # No garbage to recycle, find the highest dbnum and increment it
            # for our next free.
            return int(self.order_by('-id')[0].id + 1)

    def is_dbref(self, dbstring, require_pound=True):
        """
        Is the input a well-formed dbref number?
        """
        return util_object.is_dbref(dbstring, require_pound=require_pound)


    #
    # ObjectManager Search methods
    #

    def dbref_search(self, dbref_string, limit_types=False):
        """
        Searches for a given dbref.

        dbref_number: (string) The dbref to search for. With # sign.
        limit_types: (list of int) A list of Object type numbers to filter by.
        """
        if not util_object.is_dbref(dbref_string):
            return None
        dbref_string = dbref_string[1:]
        dbref_matches = self.filter(id=dbref_string).exclude(
                type=defines_global.OTYPE_GARBAGE)
        # Check for limiters
        if limit_types is not False:
            for limiter in limit_types:
                dbref_matches.filter(type=limiter)
        try:
            return dbref_matches[0]
        except IndexError:
            return None

    def global_object_name_search(self, ostring, exact_match=False):
        """
        Searches through all objects for a name match.
        """
        if exact_match:
            o_query = self.filter(name__iexact=ostring)
        else:
            o_query = self.filter(name__icontains=ostring)
                            
        return o_query.exclude(type__in=[defines_global.OTYPE_GARBAGE,
                                         defines_global.OTYPE_GOING])

    def global_object_script_parent_search(self, script_parent):
        """
        Searches through all objects returning those which has a certain script parent.
        """
        o_query = self.filter(script_parent__exact=script_parent)      
        return o_query.exclude(type__in=[defines_global.OTYPE_GARBAGE,
                                         defines_global.OTYPE_GOING])
    
    def list_search_object_namestr(self, searchlist, ostring, dbref_only=False, 
                                   limit_types=False, match_type="fuzzy",
                                   attribute_name=None):

        """
        Iterates through a list of objects and returns a list of
        name matches.

        This version handles search criteria of the type N-keyword, this is used
        to differentiate several objects of the exact same name, e.g. 1-box, 2-box etc.
        
        searchlist:  (List of Objects) The objects to perform name comparisons on.
        ostring:     (string) The string to match against.
        dbref_only:  (bool) Only compare dbrefs.
        limit_types: (list of int) A list of Object type numbers to filter by.
        match_type: (string) 'exact' or 'fuzzy' matching.
        attribute_name: (string) attribute name to search, if None, 'name' is used. 

        Note that the fuzzy matching gives precedence to exact matches; so if your
        search query matches an object in the list exactly, it will be the only result.
        This means that if the list contains [box,box11,box12], the search string 'box'
        will only match the first entry since it is exact. The search 'box1' will however
        match both box11 and box12 since neither is an exact match.

        Uses two helper functions, _list_search_helper1/2. 
        """
        if dbref_only:
            #search by dbref - these must always be unique.
            if limit_types:
                return [prospect for prospect in searchlist
                        if prospect.dbref_match(ostring)
                        and prospect.type in limit_types]
            else:
                return [prospect for prospect in searchlist
                        if prospect.dbref_match(ostring)]

        #search by name - this may return multiple matches.
        results = self._list_search_helper1(searchlist,ostring,dbref_only,
                                            limit_types, match_type,
                                            attribute_name=attribute_name)
        match_number = None
        if not results:
            #if we have no match, check if we are dealing
            #with a "N-keyword" query - if so, strip it and run again. 
            match_number, ostring = self._list_search_helper2(ostring)
            if match_number != None and ostring:
                results = self._list_search_helper1(searchlist,ostring,dbref_only,
                                                    limit_types, match_type,
                                                    attribute_name=attribute_name) 
        if match_type == "fuzzy":             
            #fuzzy matching; run second sweep to catch exact matches
            if attribute_name:
                exact_results = [prospect for prospect in results
                                 if ostring == prospect.get_attribute_value(attribute_name)]
            else:
                exact_results = [prospect for prospect in results
                                 if prospect.name_match(ostring, match_type="exact")]
            if exact_results:
                results = exact_results
        if len(results) > 1 and match_number != None:
            #select a particular match using the "keyword-N" markup.
            try:
                results = [results[match_number]]
            except IndexError:
                pass                        
        return results

    def _list_search_helper1(self, searchlist, ostring, dbref_only,
                             limit_types, match_type,
                             attribute_name=None):            
        """
        Helper function for list_search_object_namestr -
        does name/attribute matching through a list of objects.
        """
        if attribute_name:
            #search an arbitrary attribute name. 
            if limit_types:
                if match_type == "exact":
                    return [prospect for prospect in searchlist
                            if prospect.type in limit_types and 
                            ostring == prospect.get_attribute_value(attribute_name)]
                else:
                    return [prospect for prospect in searchlist
                            if prospect.type in limit_types and 
                            ostring in str(prospect.get_attribute_value(attribute_name))]
            else:
                if match_type == "exact":
                    return [prospect for prospect in searchlist
                            if ostring == str(prospect.get_attribute_value(attribute_name))]
                else:
                    print [type(p) for p in searchlist] 
                    return [prospect for prospect in searchlist
                            if ostring in str(prospect.get_attribute_value(attribute_name))]
        else:
            #search the default "name" attribute
            if limit_types:
                return [prospect for prospect in searchlist
                        if prospect.type in limit_types and
                        prospect.name_match(ostring, match_type=match_type)] 
            else:
                return [prospect for prospect in searchlist
                        if prospect.name_match(ostring, match_type=match_type)]

    def _list_search_helper2(self, ostring):
        """
        Hhelper function for list_search_object_namestr -
        strips eventual keyword-N endings from a search criterion
        """
        if not '-' in ostring:
            return False, ostring
        try: 
            il = ostring.find('-')
            number = int(ostring[:il])-1
            return number, ostring[il+1:]
        except ValueError:
            #not a number; this is not an identifier.
            return None, ostring
        except IndexError:
            return None, ostring 
    

    def player_alias_search(self, searcher, ostring):
        """
        Search players by alias. Returns a list of objects whose "ALIAS" 
        attribute exactly (not case-sensitive) matches ostring.
        
        searcher: (Object) The object doing the searching.
        ostring:  (string) The alias string to search for.
        """
        if ostring.lower().strip() == "me":
            return searcher
        
        Attribute = ContentType.objects.get(app_label="objects", 
                                            model="attribute").model_class()
        results = Attribute.objects.select_related().filter(attr_name__exact="ALIAS").filter(attr_value__iexact=ostring)
        return [prospect.get_object() for prospect in results if prospect.get_object().is_player()]
    
    def player_name_search(self, search_string):
        """
        Combines an alias and global search for a player's name. If there are
        no alias matches, do a global search limiting by type PLAYER.
        
        search_string:  (string) The name string to search for.
        """
        # Handle the case where someone might have started the search_string
        # with a *
        if search_string.startswith('*') is True:
            search_string = search_string[1:]
        # Use Q objects to build complex OR query to look at either
        # the player name or ALIAS attribute
        player_filter = Q(name__iexact=search_string)
        alias_filter = Q(attribute__attr_name__exact="ALIAS") & \
                Q(attribute__attr_value__iexact=search_string)
        player_matches = self.filter(
                player_filter | alias_filter).filter(
                        type=defines_global.OTYPE_PLAYER).distinct()
        try:
            return player_matches[0]
        except IndexError:
            return None


    def local_and_global_search(self, searcher, ostring, search_contents=True, 
                                search_location=True, dbref_only=False, 
                                limit_types=False, attribute_name=None):
        """
        Searches an object's location then globally for a dbref or name match.
        
        searcher: (Object) The object performing the search.
        ostring: (string) The string to compare names against.
        search_contents: (bool) While true, check the contents of the searcher.
        search_location: (bool) While true, check the searcher's surroundings.
        dbref_only: (bool) Only compare dbrefs.
        limit_types: (list of int) A list of Object type numbers to filter by.
        attribute_name: (string) Which attribute to search in each object.
                                 If None, the default 'name' attribute is used.        
        """
        search_query = str(ostring).strip()

        # This is a global dbref search. Not applicable if we're only searching
        # searcher's contents/locations, dbref comparisons for location/contents
        # searches are handled by list_search_object_namestr() below.
        if util_object.is_dbref(ostring):
            dbref_match = self.dbref_search(search_query, limit_types)
            if dbref_match is not None:
                return [dbref_match]

        # If the search string is one of the following, return immediately with
        # the appropriate result.
        if searcher.get_location().dbref_match(ostring) or ostring == 'here':
            return [searcher.get_location()]
        elif ostring == 'me' and searcher:
            return [searcher]

        if search_query[0] == "*":
            # Player search- gotta search by name or alias
            search_target = search_query[1:]
            player_match = self.player_name_search(search_target)
            if player_match is not None:
                return [player_match]
            
        # Handle our location/contents searches. list_search_object_namestr() does
        # name and dbref comparisons against search_query.
        local_objs = []
        if search_contents: 
            local_objs.extend(searcher.get_contents())
        if search_location:
            local_objs.extend(searcher.get_location().get_contents())
        return self.list_search_object_namestr(local_objs, search_query,
                                               limit_types=limit_types,
                                               attribute_name=attribute_name)        

    #
    # ObjectManager Create methods
    #

    def create_object(self, name, otype, location, owner, home=None):
        """
        Create a new object

         type:     Integer representing the object's type.
         name:     The name of the new object.
         location: Reference to another object for the new object to reside in.
         owner:    The creator of the object.
         home:     Reference to another object to home to. If not specified,  
                   set to location.
        """
        #get_nextfree_dbnum() returns either an integer or an object to recycle.
        next_dbref = self.get_nextfree_dbnum()

        if type(next_dbref) == type(int()):        
            #create object with new dbref
            Object = ContentType.objects.get(app_label="objects", 
                                         model="object").model_class()
            new_object = Object()
            new_object.id = next_dbref
        else:
            #recycle an old object's dbref
            new_object = next_dbref

        new_object.type = otype
        new_object.set_name(name)

        # If this is a player, we don't want him owned by anyone.
        # The get_owner() function will return that the player owns
        # himself.
        if otype == defines_global.OTYPE_PLAYER:
            new_object.owner = None
            new_object.zone = None
            new_object.script_parent = settings.SCRIPT_DEFAULT_PLAYER
        else:
            new_object.owner = owner
            new_object.script_parent = settings.SCRIPT_DEFAULT_OBJECT
            
            if new_object.get_owner().get_zone():
                new_object.zone = new_object.get_owner().get_zone()

        # If we have a 'home' key, use that for our home value. Otherwise use
        # the location key.
        if home:
            new_object.home = home
        else:
            if new_object.is_exit():
                new_object.home = None
            else:
                new_object.home = location
                
        new_object.save()

        # Rooms have a NULL location.
        if not new_object.is_room():
            new_object.move_to(location, quiet=True, force_look=False)
        
        return new_object

    def create_user(self, command, uname, email, password):
        """
        Handles the creation of new users.
        """
        start_room = int(ConfigValue.objects.get_configvalue('player_dbnum_start'))
        start_room_obj = self.get_object_from_dbref(start_room)

        # The user's entry in the User table must match up to an object
        # on the object table. The id's are the same, we need to figure out
        # the next free unique ID to use and make sure the two entries are
        # the same number.
        uid = self.get_nextfree_dbnum()

        # If this is an object, we know to recycle it since it's garbage. We'll
        # pluck the user ID from it.
        if not str(uid).isdigit():
            uid = uid.id
            logger.log_infomsg('Next usable object ID is %d. (recycled)' % uid)
        else:
            logger.log_infomsg('Next usable object ID is %d. (new)' % uid)

        user = User.objects.create_user(uname, email, password)
        # It stinks to have to do this but it's the only trivial way now.
        user.save()
        # We can't use the user model to change the id because of the way keys
        # are handled, so we actually need to fall back to raw SQL. Boo hiss.
        cursor = connection.cursor()
        cursor.execute("UPDATE auth_user SET id=%d WHERE id=%d" % (uid, user.id))
        
        # Update the session to use the newly created User object's ID.
        command.session.uid = uid
        logger.log_infomsg('User created with id %d.' % command.session.uid)
        
        # Grab the user object again since we've changed it and the old reference
        # is no longer valid.
        user = User.objects.get(id=uid)

        # Create a player object of the same ID in the Objects table.
        user_object = self.create_object(uname,
                                         defines_global.OTYPE_PLAYER,
                                         start_room_obj,
                                         None)

        # The User and player Object are ready, do anything needed by the
        # game to further prepare things.
        user_object.scriptlink.at_player_creation()

        # Activate the player's session and set them loose.
        command.session.login(user)
        
        logger.log_infomsg('Registration: %s' % user_object.get_name())

        #Don't show the greeting; it messes with using the login hooks for
        #making character creation wizards. /Griatch
        #user_object.emit_to("Welcome to %s, %s.\n\r" % (
        #    ConfigValue.objects.get_configvalue('site_name'), 
        #    user_object.get_name(show_dbref=False)))
        
        # Add the user to all of the CommChannel objects that are flagged
        # is_joined_by_default.
        command.session.add_default_channels()
