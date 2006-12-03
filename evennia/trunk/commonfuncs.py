from apps.objects.models import Object, Attribute

def list_search_object_str(searchlist, ostring):
   [prospect for prospect in searchlist if prospect.name_match(ostring)]
