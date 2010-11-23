#
# This module implements a simple news entry system
# for the evennia website. One needs to use the 
# admin interface to add/edit/delete entries. 
#

from django.db import models
from django.contrib.auth.models import User

class NewsTopic(models.Model):
    """
    Represents a news topic.
    """
    name = models.CharField(max_length=75, unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='newstopic_icons', 
                             default='newstopic_icons/default.png', 
                             blank=True, help_text="Image for the news topic.")

    def __str__(self):
        try:
            return self.name
        except:
            return "Invalid"

    class Meta:
        ordering = ['name']

class NewsEntry(models.Model):
    """
    An individual news entry.
    """
    author = models.ForeignKey(User, related_name='author')
    title = models.CharField(max_length=255)
    body = models.TextField()
    topic = models.ForeignKey(NewsTopic, related_name='newstopic')
    date_posted = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

    class Meta:
        ordering = ('-date_posted',)
        verbose_name_plural = "News entries"

