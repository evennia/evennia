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
      
def local_and_global_search(object, ostring):
   """
   Searches an object's location then globally for a dbref or name match.
   """
   search_query = ''.join(ostring)
   
   local_matches = list_search_object_namestr(object.location.contents_list, search_query)
   
   # If the object the invoker is in matches, add it as well.
   if object.location.dbref_match(ostring) or ostring == 'here':
      local_matches.append(object.location)
   
   global_matches = []
   if is_dbref(ostring):
      global_matches = list(Object.objects.filter(id=search_query))
   
   return local_matches + global_matches

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
   
   
