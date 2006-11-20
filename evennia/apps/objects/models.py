from django.db import models
from django.contrib.auth.models import User

class ObjectClass(models.Model):
   """
   Each object class can have different behaviors to apply to it.
   """
   name = models.CharField(maxlength=255)
   description = models.TextField()
   
   def __str__(self):
      return "%s(%d)" % (self.name, self.id,)
   
   class Admin:
      list_display = ('name', 'description',)

class Attribute(models.Model):
   """
   Attributes are things that are specific to different types of objects. For
   example, a drink container needs to store its fill level, whereas an exit
   needs to store its open/closed/locked/unlocked state. These are done via
   attributes, rather than making different classes for each object type and
   storing them directly. The added benefit is that we can add/remove attributes
   on the fly as we like.
   """
   name = models.CharField(maxlength=255)
   value = models.CharField(maxlength=255)
   object = models.ForeignKey("Object")
   
   def __str__(self):
      return "%s(%d)" % (self.name, self.id,)
   
   class Admin:
      list_display = ('name', 'value',)

class Object(models.Model):
   """
   The Object class is very generic. We put all of our common attributes
   here and anything very particular into the attribute field. Notice the otype
   field. The different otypes denote an object's behaviors.
   """
   
   # Do not mess with the default types (0-4).
   OBJECT_TYPES = (
      (0, 'NOTHING'),
      (1, 'PLAYER'),
      (2, 'ROOM'),
      (3, 'THING'),
      (4, 'EXIT'),
   )
   
   name = models.CharField(maxlength=255)
   type = models.SmallIntegerField(choices=OBJECT_TYPES)
   description = models.TextField(blank=True)
   location = models.ForeignKey('self', related_name="olocation", blank=True, null=True)
   contents = models.ManyToManyField("Object", related_name="object", blank=True, null=True)
   attributes = models.ManyToManyField(Attribute, related_name="attributes", blank=True, null=True)
   
   def __str__(self):
      return "%s(%d)" % (self.name, self.id,)
      
   def is_type(self, typename):
      """
      Do a string comparison of user's input and the object's type class object's
      name.
      """
      return self.type.name == typename
      
   def set_type(self, typename):
      """
      Sets a object's type.
      """
      pass
   
   class Admin:
      list_display = ('name',)
"""
class Player(models.Model):
# 
#   Model representation of our players.
#
   # Link back to our Django User class for password, username, email, etc.
   account = models.ForeignKey(User)
   location = models.ForeignKey(Object, related_name="plocation")
   is_connected = models.BooleanField()
   last_connected = models.DateTimeField()
   contents = models.ManyToManyField(Object)
   attributes = models.ManyToManyField(Attribute)

   def __str__(self):
      return "%s(%d)" % (self.name, self.id,)
"""
