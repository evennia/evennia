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
   def move_to(self, target):
      """
      Moves the object to a new location.
      """
      self.location.contents_list.remove(self)
      self.location = target
      target.contents_list.append(self)
      self.save()
      
   def dbref_match(self, oname):
      import functions_db
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
      import functions_db
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
   
   def __str__(self):
      return "%s(%d)" % (self.name, self.id,)
