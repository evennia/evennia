import sets
from django.contrib.auth.models import User
from apps.objects.models import Object
import global_defines

def modifiable_flag(flagname):
   """
   Check to see if a particular flag is modifiable.
   """
   if flagname not in global_defines.NOSET_FLAGS:
      return True
   else:
      return False

def get_nextfree_dbnum():
   """
   Figure out what our next free database reference number is.
   """
   # First we'll see if there's an object of type 5 (GARBAGE) that we
   # can recycle.
   nextfree = Object.objects.filter(type__exact=5)
   if nextfree:
      # We've got at least one garbage object to recycle.
      #return nextfree.id
      return nextfree[0].id
   else:
      # No garbage to recycle, find the highest dbnum and increment it
      # for our next free.
      return Object.objects.order_by('-id')[0].id + 1

def list_search_object_namestr(searchlist, ostring, dbref_only=False):
   """
   Iterates through a list of objects and returns a list of
   name matches.
   """
   if dbref_only:
      return [prospect for prospect in searchlist if prospect.dbref_match(ostring)]
   else:
      return [prospect for prospect in searchlist if prospect.name_match(ostring)]
      
def local_and_global_search(object, ostring, local_only=False, searcher=None):
   """
   Searches an object's location then globally for a dbref or name match.
   local_only: Only compare the objects in the player's location if True.
   """
   search_query = ''.join(ostring)

   if is_dbref(ostring) and not local_only:
      search_num = search_query[1:]
      dbref_match = list(Object.objects.filter(id=search_num))
      if len(dbref_match) > 0:
         return dbref_match

   local_matches = list_search_object_namestr(object.location.get_contents(), search_query)
   
   # If the object the invoker is in matches, add it as well.
   if object.location.dbref_match(ostring) or ostring == 'here':
      local_matches.append(object.location)
   elif ostring == 'me' and searcher:
      local_matches.append(searcher)
   
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
   
def session_from_object(session_list, targobject):
   """
   Return the session object given a object (if there is one open).
   """
   results = [prospect for prospect in session_list if prospect.pobject == targobject]
   if results:
      return results[0]
   else:
      return False

def session_from_dbref(session_list, dbstring):
   """
   Return the session object given a dbref (if there is one open).
   """
   if is_dbref(dbstring):
      results = [prospect for prospect in session_list if prospect.pobject.dbref_match(dbstring)]
      if results:
         return results[0]
   else:
      return False
      
def get_object_from_dbref(server, dbref):
   """
   Returns an object when given a dbref.
   """
   return server.object_list.get(dbref, False)
   
def create_object(server, odat):
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
   new_object = Object()
   new_object.name = odat["name"]
   new_object.type = odat["type"]

   # If this is a player, set him to own himself.
   if odat["type"] == 1:
      new_object.owner = None
      new_object.zone = None
   else:
      new_object.owner = odat["owner"]
      
      if new_object.owner.zone:
         new_object.zone = new_object.owner.zone

   # If we have a 'home' key, use that for our home value. Otherwise use
   # the location key.
   if odat.get("home",False):
      new_object.home = odat["home"]
   else:
      new_object.home = odat["location"]
         
   new_object.save()
   
   # Add the object to our server's dictionary of objects.
   server.add_object_to_cache(new_object)
   new_object.move_to(server, odat['location'])
   
   return new_object

def create_user(cdat, uname, email, password):
   """
   Handles the creation of new users.
   """
   session = cdat['session']
   server = cdat['server']
   start_room = int(server.get_configvalue('player_dbnum_start'))
   start_room_obj = get_object_from_dbref(server, start_room)

   # The user's entry in the User table must match up to an object
   # on the object table. The id's are the same, we need to figure out
   # the next free unique ID to use and make sure the two entries are
   # the same number.
   uid = get_nextfree_dbnum()
   user = User.objects.create_user(uname, email, password)
   # It stinks to have to do this but it's the only trivial way now.
   user.id = uid
   user.save

   # Create a player object of the same ID in the Objects table.
   odat = {"id": uid, "name": uname, "type": 1, "location": start_room_obj, "owner": None}
   user_object = functions_db.create_object(server, odat)

   # Activate the player's session and set them loose.
   session.login(user)
   print 'Registration: %s' % (session,)
   session.push("Welcome to %s, %s.\n\r" % (server.get_configvalue('site_name'), session.name,))
