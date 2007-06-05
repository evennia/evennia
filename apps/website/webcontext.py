from django.conf import settings

def general_context(request):
   """
   Returns common Evennia-related context stuff.
   """
   return {
      'game_name': "Test Game",
      'media_url': settings.MEDIA_URL,
   }
