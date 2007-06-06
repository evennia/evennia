import sets
from datetime import datetime, timedelta

from django.db import connection
from django.contrib.auth.models import User
from apps.objects.models import Object, Attribute
import defines_global as defines_global
import gameconf

"""
Common database functions.
"""
def num_total_players():
   """
   Returns the total number of registered players.
   """
   return User.objects.count()

def get_connected_players():
   """
   Returns the a QuerySet containing the currently connected players.
   """
   return Object.objects.filter(nosave_flags__contains="CONNECTED")

def num_connected_players():
   """
   Returns the number of connected players.
   """
   return get_connected_players().count()

def num_recently_created_players(days=7):
   """
   Returns a QuerySet containing the player User accounts that have been
   connected within the last <days> days.
   """
   end_date = datetime.now()
   tdelta = timedelta(days)
   start_date = end_date - tdelta
   return User.objects.filter(date_joined__range=(start_date, end_date)).count()

def num_recently_connected_players(days=7):
   """
   Returns a QuerySet containing the player User accounts that have been
   connected within the last <days> days.
   """
   end_date = datetime.now()
   tdelta = timedelta(days)
   start_date = end_date - tdelta
   return User.objects.filter(last_login__range=(start_date, end_date)).count()

def is_unsavable_flag(flagname):
   """
   Returns TRUE if the flag is an unsavable flag.
   """
   return flagname.upper() in defines_global.NOSAVE_FLAGS

def is_modifiable_flag(flagname):
   """
   Check to see if a particular flag is modifiable.
   """
   if flagname.upper() not in defines_global.NOSET_FLAGS:
      return True
   else:
      return False
      
def is_modifiable_attrib(attribname):
   """
   Check to see if a particular attribute is modifiable.

   attribname: (string) An attribute name to check.
   """
   if attribname.upper() not in defines_global.NOSET_ATTRIBS:
      return True
   else:
      return False
      
def get_nextfree_dbnum():
   """
   Figure out what our next free database reference number is.
   
   If we need to recycle a GARBAGE object, return the object to recycle
   Otherwise, return the first free dbref.
   """
   # First we'll see if there's an object of type 6 (GARBAGE) that we
   # can recycle.
   nextfree = Object.objects.filter(type__exact=defines_global.OTYPE_GARBAGE)
   if nextfree:
      # We've got at least one garbage object to recycle.
      return nextfree[0]
   else:
      # No garbage to recycle, find the highest dbnum and increment it
      # for our next free.
      return int(Object.objects.order_by('-id')[0].id + 1)

def global_object_name_search(ostring, exact_match=False):
   """
   Searches through all objects for a name match.
   """
   if exact_match:
      return Object.objects.filter(name__iexact=ostring).exclude(type=defines_global.OTYPE_GARBAGE)
   else:
      return Object.objects.filter(name__icontains=ostring).exclude(type=defines_global.OTYPE_GARBAGE)
   
def list_search_object_namestr(searchlist, ostring, dbref_only=False, limit_types=False, match_type="fuzzy"):
   """
   Iterates through a list of objects and returns a list of
   name matches.
   searchlist: (List of Objects) The objects to perform name comparisons on.
   ostring:    (string) The string to match against.
   dbref_only: (bool) Only compare dbrefs.
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

def player_search(searcher, ostring):
   """
   Combines an aias and local/global search for a player's name.
   searcher: (Object) The object doing the searching.
   ostring:  (string) The alias string to search for.
   """
   alias_results = alias_search(searcher, ostring)
   if len(alias_results) > 0:
      return alias_results
   else:
      return local_and_global_search(searcher, ostring, limit_types=[defines_global.OTYPE_PLAYER])

def standard_plr_objsearch(session, ostring, search_contents=True, search_location=True, dbref_only=False, limit_types=False):
   """
   Perform a standard object search via a player session, handling multiple
   results and lack thereof gracefully.

   session: (SessionProtocol) Reference to the player's session.
   ostring: (str) The string to match object names against.
   """
   pobject = session.get_pobject()
   results = local_and_global_search(pobject, ostring, search_contents=search_contents, search_location=search_location, dbref_only=dbref_only, limit_types=limit_types)

   if len(results) > 1:
      session.msg("More than one match found (please narrow target):")
      for result in results:
         session.msg(" %s" % (result.get_name(),))
      return False
   elif len(results) == 0:
      session.msg("I don't see that here.")
      return False
   else:
      return results[0]

def object_totals():
   """
   Returns a dictionary with database object totals.
   """
   dbtotals = {}
   dbtotals["objects"] = Object.objects.count()
   dbtotals["things"] = Object.objects.filter(type=defines_global.OTYPE_THING).count()
   dbtotals["exits"] = Object.objects.filter(type=defines_global.OTYPE_EXIT).count()
   dbtotals["rooms"] = Object.objects.filter(type=defines_global.OTYPE_ROOM).count()
   dbtotals["garbage"] = Object.objects.filter(type=defines_global.OTYPE_GARBAGE).count()
   dbtotals["players"] = Object.objects.filter(type=defines_global.OTYPE_PLAYER).count()
   return dbtotals

def alias_search(searcher, ostring):
   """
   Search players by alias. Returns a list of objects whose "ALIAS" attribute
   exactly (not case-sensitive) matches ostring. If there isn't an alias match,
   perform a local_and_global_search().
   
   searcher: (Object) The object doing the searching.
   ostring:  (string) The alias string to search for.
   """
   search_query = ''.join(ostring)
   results = Attribute.objects.select_related().filter(attr_value__iexact=ostring)
   return [prospect.get_object() for prospect in results if prospect.get_object().is_player()]
      
def local_and_global_search(searcher, ostring, search_contents=True, search_location=True, dbref_only=False, limit_types=False):
   """
   Searches an object's location then globally for a dbref or name match.
   
   searcher: (Object) The object performing the search.
   ostring: (string) The string to compare names against.
   search_contents: (bool) While true, check the contents of the searcher.
   search_location: (bool) While true, check the searcher's surroundings.
   dbref_only: (bool) Only compare dbrefs.
   limit_types: (list of int) A list of Object type numbers to filter by.
   """
   search_query = ''.join(ostring)

   # This is a global dbref search. Not applicable if we're only searching
   # searcher's contents/locations, dbref comparisons for location/contents
   # searches are handled by list_search_object_namestr() below.
   if is_dbref(ostring) and search_contents and search_location:
      search_num = search_query[1:]
      dbref_results = Object.objects.filter(id=search_num).exclude(type=6)

      # If there is a type limiter in, filter by it.
      if limit_types:
         for limiter in limit_types:
            dbref_results.filter(type=limiter)
            
      dbref_match = list(dbref_results)
      if len(dbref_match) > 0:
         return dbref_match

   # If the search string is one of the following, return immediately with
   # the appropriate result.
   if searcher.get_location().dbref_match(ostring) or ostring == 'here':
      return [searcher.get_location()]
   elif ostring == 'me' and searcher:
      return [searcher]

   local_matches = []
   # Handle our location/contents searches. list_search_object_namestr() does
   # name and dbref comparisons against search_query.
   if search_contents: 
      local_matches += list_search_object_namestr(searcher.get_contents(), search_query, limit_types)
   if search_location:
      local_matches += list_search_object_namestr(searcher.get_location().get_contents(), search_query, limit_types=limit_types)
   
   return local_matches

def is_dbref(dbstring):
   """
   Is the input a well-formed dbref number?
   """
   try:
      number = int(dbstring[1:])
   except ValueError:
      return False
   
   if dbstring[0] != '#':
      return False
   elif number < 1:
      return False
   else:
      return True
   
def get_user_from_email(uemail):
   """
   Returns a player's User object when given an email address.
   """
   return User.objects.filter(email__iexact=uemail)

def get_object_from_dbref(dbref):
   """
   Returns an object when given a dbref.
   """
   return Object.objects.get(id=dbref)
   
def create_object(odat):
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
   next_dbref = get_nextfree_dbnum()
   if not str(next_dbref).isdigit():
      # Recycle a garbage object.
      new_object = next_dbref
   else:
      new_object = Object()
      
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

def create_user(cdat, uname, email, password):
   """
   Handles the creation of new users.
   """
   session = cdat['session']
   server = cdat['server']
   start_room = int(gameconf.get_configvalue('player_dbnum_start'))
   start_room_obj = get_object_from_dbref(start_room)

   # The user's entry in the User table must match up to an object
   # on the object table. The id's are the same, we need to figure out
   # the next free unique ID to use and make sure the two entries are
   # the same number.
   uid = get_nextfree_dbnum()
   print 'UID', uid

   # If this is an object, we know to recycle it since it's garbage. We'll
   # pluck the user ID from it.
   if not str(uid).isdigit():
      uid = uid.id
   print 'UID2', uid

   user = User.objects.create_user(uname, email, password)
   # It stinks to have to do this but it's the only trivial way now.
   user.save()
   
   # We can't use the user model to change the id because of the way keys
   # are handled, so we actually need to fall back to raw SQL. Boo hiss.
   cursor = connection.cursor()
   cursor.execute("UPDATE auth_user SET id=%d WHERE id=%d" % (uid, user.id))
   
   # Grab the user object again since we've changed it and the old reference
   # is no longer valid.
   user = User.objects.get(id=uid)

   # Create a player object of the same ID in the Objects table.
   odat = {"id": uid, "name": uname, "type": 1, "location": start_room_obj, "owner": None}
   user_object = create_object(odat)

   # Activate the player's session and set them loose.
   session.login(user)
   print 'Registration: %s' % (session,)
   session.msg("Welcome to %s, %s.\n\r" % (gameconf.get_configvalue('site_name'), session.get_pobject().get_name(show_dbref=False),))
