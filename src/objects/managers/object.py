"""
Custom manager for Object objects.
"""
import sets
from datetime import datetime, timedelta

from django.db import models
from django.db import connection
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from src.config.models import ConfigValue
from src.objects.exceptions import ObjectNotExist
from src.objects.util import object as util_object
from src import defines_global

class ObjectManager(models.Manager):
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
            return nextfree.id
        else:
            # No garbage to recycle, find the highest dbnum and increment it
            # for our next free.
            return int(self.order_by('-id')[0].id + 1)

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
        
    def list_search_object_namestr(self, searchlist, ostring, dbref_only=False, 
                                   limit_types=False, match_type="fuzzy"):
        """
        Iterates through a list of objects and returns a list of
        name matches.
        searchlist:  (List of Objects) The objects to perform name comparisons on.
        ostring:     (string) The string to match against.
        dbref_only:  (bool) Only compare dbrefs.
        limit_types: (list of int) A list of Object type numbers to filter by.
        """
        if dbref_only:
            if limit_types:
                return [prospect for prospect in searchlist if prospect.dbref_match(ostring) and prospect.type in limit_types]
            else:
                return [prospect for prospect in searchlist if prospect.dbref_match(ostring)]
        else:
            if limit_types:
                return [prospect for prospect in searchlist if prospect.name_match(ostring, match_type=match_type) and prospect.type in limit_types]
            else:
                return [prospect for prospect in searchlist if prospect.name_match(ostring, match_type=match_type)]

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

    def is_dbref(self, dbstring, require_pound=True):
        """
        Is the input a well-formed dbref number?
        """
        return util_object.is_dbref(dbstring, require_pound=require_pound)

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

    def local_and_global_search(self, searcher, ostring, search_contents=True, 
                                search_location=True, dbref_only=False, 
                                limit_types=False):
        """
        Searches an object's location then globally for a dbref or name match.
        
        searcher: (Object) The object performing the search.
        ostring: (string) The string to compare names against.
        search_contents: (bool) While true, check the contents of the searcher.
        search_location: (bool) While true, check the searcher's surroundings.
        dbref_only: (bool) Only compare dbrefs.
        limit_types: (list of int) A list of Object type numbers to filter by.
        """
        search_query = ostring

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

        local_matches = []
        # Handle our location/contents searches. list_search_object_namestr() does
        # name and dbref comparisons against search_query.
        if search_contents: 
            local_matches += self.list_search_object_namestr(searcher.get_contents(), 
                                        search_query, limit_types)
        if search_location:
            local_matches += self.list_search_object_namestr(searcher.get_location().get_contents(), 
                                        search_query, limit_types=limit_types)
        return local_matches
        
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
        
    def create_object(self, odat):
        """
        Create a new object. odat is a dictionary that contains the following keys.
        REQUIRED KEYS:
         * type: Integer representing the object's type.
         * name: The name of the new object.
         * location: Reference to another object for the new object to reside in.
         * owner: The creator of the object.
        OPTIONAL KEYS:
         * home: Reference to another object to home to. If not specified, use 
            location key for home.
        """
        next_dbref = self.get_nextfree_dbnum()
        Object = ContentType.objects.get(app_label="objects", 
                                            model="object").model_class()
        new_object = Object()

        new_object.id = next_dbref
        new_object.type = odat["type"]
        new_object.set_name(odat["name"])

        # If this is a player, we don't want him owned by anyone.
        # The get_owner() function will return that the player owns
        # himself.
        if odat["type"] == 1:
            new_object.owner = None
            new_object.zone = None
        else:
            new_object.owner = odat["owner"]
            
            if new_object.get_owner().get_zone():
                new_object.zone = new_object.get_owner().get_zone()

        # If we have a 'home' key, use that for our home value. Otherwise use
        # the location key.
        if odat.has_key("home"):
            new_object.home = odat["home"]
        else:
            if new_object.is_exit():
                new_object.home = None
            else:
                new_object.home = odat["location"]
                
        new_object.save()

        # Rooms have a NULL location.
        if not new_object.is_room():
            new_object.move_to(odat['location'])
        
        return new_object

    def create_user(self, command, uname, email, password):
        """
        Handles the creation of new users.
        """
        session = command.session
        server = command.server
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

        user = User.objects.create_user(uname, email, password)
        # It stinks to have to do this but it's the only trivial way now.
        user.save()
        # Update the session to use the newly created User object's ID.
        session.uid = user.id
        
        # We can't use the user model to change the id because of the way keys
        # are handled, so we actually need to fall back to raw SQL. Boo hiss.
        cursor = connection.cursor()
        cursor.execute("UPDATE auth_user SET id=%d WHERE id=%d" % (uid, user.id))
        
        # Grab the user object again since we've changed it and the old reference
        # is no longer valid.
        user = User.objects.get(id=uid)

        # Create a player object of the same ID in the Objects table.
        odat = {"id": uid, 
                "name": uname, 
                "type": defines_global.OTYPE_PLAYER, 
                "location": start_room_obj, 
                "owner": None}
        user_object = self.create_object(odat)

        # Activate the player's session and set them loose.
        session.login(user)
        print 'Registration: %s' % (session,)
        session.msg("Welcome to %s, %s.\n\r" % (
            ConfigValue.objects.get_configvalue('site_name'), 
            session.get_pobject().get_name(show_dbref=False)))
        session.add_default_channels()