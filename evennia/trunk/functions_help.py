from apps.helpsys.models import HelpEntry
"""
Help system functions.
"""
def find_topicmatch(topicstr, pobject):
   """
   Searches for matching topics based on player's input.
   """
   if topicstr.isdigit():
      return HelpEntry.objects.filter(id=topicstr)
   else:
      return HelpEntry.objects.filter(topicname__istartswith=topicstr)
   
def find_topicsuggestions(topicstr, pobject):
   """
   Do a fuzzier "contains" match.
   """
   return HelpEntry.objects.filter(topicname__icontains=topicstr)
