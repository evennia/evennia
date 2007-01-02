from django.db import models
import ansi

class HelpEntry(models.Model):
   """
   A generic help entry.
   """
   topicname = models.CharField(maxlength=255)
   entrytext = models.TextField(blank=True, null=True)
   staff_only = models.BooleanField(default=0)

   class Admin:
      list_display = ('id', 'topicname', 'staff_only')
      list_filter = ('staff_only',)
      search_fields = ['entrytext']
      
   class Meta:
      verbose_name_plural = "Help entries"
      ordering = ['topicname']
      
   def __str__(self):
      return self.topicname
      
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
