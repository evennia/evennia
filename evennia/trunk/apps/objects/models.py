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
   
   # Do not mess with the default types (0-5).
   OBJECT_TYPES = (
      (0, 'NOTHING'),
      (1, 'PLAYER'),
      (2, 'ROOM'),
      (3, 'THING'),
      (4, 'EXIT'),
      (5, 'GARBAGE'),
   )
   
   name = models.CharField(maxlength=255)
   type = models.SmallIntegerField(choices=OBJECT_TYPES)
   description = models.TextField(blank=True)
   location = models.ForeignKey('self', related_name="olocation", blank=True, null=True)
   
   # Rather than keeping another relation for this, we're just going to use
   # foreign keys and populate each object's contents and attribute lists at
   # server startup. It'll keep some of the tables more simple, but at the
   # cost of a little bit more memory usage. No biggy.
   
   # A list of objects located inside the object.
   contents_list = []
   # A dictionary of attributes assocated with the object. The keys are the
   # attribute's names.
   attrib_list = {}
   
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
