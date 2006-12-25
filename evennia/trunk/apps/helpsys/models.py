from django.db import models
import ansi

# Create your models here.
class HelpEntry(models.Model):
   """
   A generic help entry.
   """
   topicname = models.CharField(maxlength=255)
   entrytext = models.TextField(blank=True, null=True)
   staff_only = models.BooleanField(default=0)
   
   def __str__(self):
      return "%3d. %s" % (self.id, self.topicname)

   def get_topicname(self):
      """
      Returns the topic's name.
      """
      try:
         return self.topicname
      except:
         return None
   
   def get_entrytext_ingame(self):
      """
      Gets the entry text for in-game viewing.
      """
      try:
         return ansi.parse_ansi(self.entrytext)
      except:
         return None
