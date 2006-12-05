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
   
   def __cmp__(self, other):
      """
      Used to figure out if one object is the same as another.
      """
      return self.id == other.id
   
   class Meta:
      permissions = (
         ("can_examine", "Can examine objects"),
      )
   
   class Admin:
      list_display = ('name',)
   
   """
   BEGIN COMMON METHODS
   """
   def load_to_location(self):
      """
      Adds an object to its location.
      """ 
      print 'Adding %s to %s.' % (self.id, self.location.id,)
      self.location.contents_list.append(self)
      
   def get_contents(self):
      """
      Returns the contents of an object.
      
      TODO: Make this use the object's contents_list field. There's
      something horribly long with the load routine right now.
      """
      return list(Object.objects.filter(location__id=self.id))
   
   def move_to(self, server, target):
      """
      Moves the object to a new location. We're going to modify the server's
      cached version of the object rather than the one we're given due
      to the way references are passed. We can firm this up by other means
      but this is more or less fool-proof for now.
      """
      #if self in self.location.contents_list:
      #   self.location.contents_list.remove(self)
      #target.contents_list.append(self)
      
      cached_object = functions_db.get_object_from_dbref(server, self.id)
      cached_object.location = target
      cached_object.save()
      
   def dbref_match(self, oname):
      """
      Check if the input (oname) can be used to identify this particular object
      by means of a dbref match.
      """
      if not functions_db.is_dbref(oname):
         return False
         
      try:
         is_match = int(oname[1:]) == self.id
      except ValueError:
         return false
         
      return is_match
      
   def name_match(self, oname):
      """   
      See if the input (oname) can be used to identify this particular object.
      Check the # sign for dbref (exact) reference, and anything else is a
      name comparison.
      
      NOTE: A 'name' can be a dbref or the actual name of the object. See
      dbref_match for an exclusively name-based match.
      """
      if oname[0] == '#':
         return self.dbref_match(oname)
      else:
         return oname.lower() in self.name.lower()
         
   def filter_contents_from_str(self, oname):
      """
      Search an object's contents for name and dbref matches. Don't put any
      logic in here, we'll do that from the end of the command or function.
      """
      return [prospect for prospect in self.contents_list if prospect.name_match(oname)]

   # Type comparison methods.
   def is_player(self):
      return self.type is 1
   def is_room(self):   
      return self.type is 2
   def is_thing(self):
      return self.type is 3
   def is_exit(self):
      return self.type is 4
   def is_garbage(self):
      return self.type is 5
      
   def is_type(self, otype):
      """
      See if an object is a certain type.
      """
      otype = otype[0]
      
      if otype is 'p':
         return self.is_player()
      elif otype is 'r':
         return self.is_room()
      elif otype is 't':
         return self.is_thing()
      elif otype is 'e':
         return self.is_exit()
      elif otype is 'g':
         return self.is_garbage()

   def __str__(self):
      return "%s(%d)" % (self.name, self.id,)

import functions_db
