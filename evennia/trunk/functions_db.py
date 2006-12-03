import sets
from apps.objects.models import Object

def list_search_object_namestr(searchlist, ostring, dbref_only=False):
   """
   Iterates through a list of objects and returns a list of
   name matches.
   """
   if dbref_only:
      return [prospect for prospect in searchlist if prospect.dbref_match(ostring)]
   else:
      return [prospect for prospect in searchlist if prospect.name_match(ostring)]
      
def local_and_global_search(object, ostring, local_only=False):
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

   local_matches = list_search_object_namestr(object.location.contents_list, search_query)
   
   # If the object the invoker is in matches, add it as well.
   if object.location.dbref_match(ostring) or ostring == 'here':
      local_matches.append(object.location)
   
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
   
   
