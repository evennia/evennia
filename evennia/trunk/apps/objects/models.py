from django.db import models
from django.contrib.auth.models import User
import global_defines

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
   is_hidden = models.BooleanField(default=0)
   object = models.ForeignKey("Object")
   
   def __str__(self):
      return "%s(%d)" % (self.name, self.id,)
   
   class Admin:
      list_display = ('name', 'value',)

class Object(models.Model):
   """
   The Object class is very generic representation of a THING, PLAYER, EXIT,
   ROOM, or other entities within the database. Pretty much anything in the
   game is an object. Objects may be one of several different types, and
   may be parented to allow for differing behaviors.
   
   We eventually want to find some way to implement object parents via loadable 
   modules or sub-classing.
   """
   name = models.CharField(maxlength=255)
   owner = models.ForeignKey('self', related_name="obj_owner", blank=True, null=True)
   zone = models.ForeignKey('self', related_name="obj_zone", blank=True, null=True)
   home = models.ForeignKey('self', related_name="obj_home", blank=True, null=True)
   type = models.SmallIntegerField(choices=global_defines.OBJECT_TYPES)
   description = models.TextField(blank=True)
   location = models.ForeignKey('self', related_name="obj_location", blank=True, null=True)
   flags = models.TextField(blank=True)
   nosave_flags = models.TextField(blank=True)
   date_created = models.DateField(editable=False, auto_now_add=True)

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
   def emit_to(self, message):
      """
      Emits something to any sessions attached to the object.
      
      message: (str) The message to send
      """
   
   def is_staff(self):
      """
      Returns TRUE if the object is a staff player.
      """
      if not self.is_player():
         return False
      
      profile = User.objects.filter(id=self.id)
      
      if len(profile) == 0:
         return False
      else:
         return profile[0].is_staff

   def is_superuser(self):
      """
      Returns TRUE if the object is a super user player.
      """
      if not self.is_player():
         return False
      
      profile = User.objects.filter(id=self.id)
      
      if len(profile) == 0:
         return False
      else:
         return profile[0].is_superuser

   def set_name(self, new_name):
      """
      Rename an object.
      """
      self.name = new_name
      self.save()
      
      # If it's a player, we need to update their user object as well.
      if self.is_player():
         pobject = User.objects.get(id=self.id)
         pobject.name = new_name
         pobject.save()
            
   def get_name(self):
      """
      Returns an object's name.
      """
      return self.name
   
   def get_flags(self):
      """
      Returns an object's flag list.
      """
      return '%s %s' % (self.flags, self.nosave_flags)
      
   def clear_attribute(self, attribute):
      """
      Removes an attribute entirely.
      
      attribute: (str) The attribute's name.
      """
      if self.has_attribute(attribute):
         attrib_obj = self.get_attribute_obj(attribute)
         attrib_obj.delete()
         return True
      else:
         return False
         
   def clear_all_attributes(self):
      """
      Clears all of an object's attributes.
      """
      attribs = Attribute.objects.filter(object=self)
      for attrib in attribs:
         self.delete()
         
   def get_all_attributes(self):
      """
      Returns a QuerySet of an object's attributes.
      """
      attribs = Attribute.objects.filter(object=self)
      return attribs
   
   def destroy(self, session_list):   
      """
      Destroys an object, sets it to GOING. Can still be recovered
      if the user decides to.
      
      session_list: (list) The server's session_list attribute.
      """
      
      # See if we need to kick the player off.
      session = functions_db.session_from_object(session_list, self)
      if session:
         session.msg("You have been destroyed, goodbye.")
         session.handle_close()
         
      # If the object is a player, set the player account object to inactive.
      # It can still be recovered at this point.      
      if self.is_player():
         print 'PLAYER'
         uobj = User.objects.get(id=self.id)
         print 'VICTIM', uobj
         uobj.is_active = False
         uobj.save()
         
      # Set the object type to GOING
      self.type = 5
      self.save()
           
   def delete(self, session_list):
      """
      Deletes an object permanently. Marks it for re-use by a new object.
      
      session_list: (list) The server's session_list attribute.
      """
      # Delete the associated player object permanently.
      uobj = User.objects.filter(id=self.id)
      if len(uobj) > 0:
         uobj[0].delete()
         
      # Set the object to type GARBAGE.
      self.type = 6
      self.save()
      self.clear_all_attributes()
      
   def set_attribute(self, attribute, new_value):
      """
      Sets an attribute on an object. Creates the attribute if need
      be.
      
      attribute: (str) The attribute's name.
      new_value: (str) The value to set the attribute to.
      """
      if self.has_attribute(attribute):
         # Attribute already exists, update it.
         attrib_obj = Attribute.objects.filter(object=self).filter(name=attribute)
         attrib_obj.value = new_value
         attrib_obj.save()
      else:
         # Attribute object doesn't exist, create it.
         new_attrib = Attribute()
         new_attrib.name = attribute
         new_attrib.value = new_value
         new_attrib.object = self
         new_attrib.save()
         
   def has_attribute(self, attribute):
      """
      See if we have an attribute set on the object.
      
      attribute: (str) The attribute's name.
      """
      attr = Attribute.objects.filter(object=self).filter(name=attribute)
      if attr.count() == 0:
         return False
      else:
         return True
      
   def has_flag(self, flag):
      """
      Does our object have a certain flag?
      
      flag: (str) Flag name
      """
      return flag in self.flags or flag in self.nosave_flags
      
   def set_flag(self, flag, value):
      """
      Add a flag to our object's flag list.
      
      flag: (str) Flag name
      value: (bool) Set (True) or un-set (False)
      """
      flag = flag.upper()
      has_flag = self.has_flag(flag)
      
      if value == False and has_flag:
         # Clear the flag.
         if functions_db.is_unsavable_flag(flag):
            # Not a savable flag (CONNECTED, etc)
            flags = self.nosave_flags.split()
            flags.remove(flag)
            self.nosave_flags = ' '.join(flags)
         else:
            # Is a savable flag.
            flags = self.flags.split()
            flags.remove(flag)
            self.flags = ' '.join(flags)
         self.save()
         
      elif value == False and not has_flag:
         # Object doesn't have the flag to begin with.
         pass
      elif value == True and has_flag:
         # We've already go it.
         pass
      else:
         # Setting a flag.
         if functions_db.is_unsavable_flag(flag):
            # Not a savable flag (CONNECTED, etc)
            flags = self.nosave_flags.split()
            flags.append(flag)
            self.nosave_flags = ' '.join(flags)
         else:
            # Is a savable flag.
            flags = self.flags.split()
            flags.append(flag)
            self.flags = ' '.join(flags)
         self.save()
   
   def get_owner(self):
      """
      Returns an object's owner.
      """
      # Players always own themselves.
      if self.is_player():
         return self
      else:
         return self.owner
   
   def get_home(self):
      """
      Returns an object's home.
      """
      return self.home
   
   def get_location(self):
      """
      Returns an object's location.
      """
      return self.location
         
   def get_attribute_value(self, attrib, default=False):
      """
      Returns the value of an attribute on an object.
      
      attrib: (str) The attribute's name.
      """
      if self.has_attribute(attrib):
         attrib = Attribute.objects.filter(object=self).filter(name=attrib)
         attrib_value = attrib[0].value
         return attrib_value.value
      else:
         if default:
            return default
         else:
            return False
         
   def get_attribute_obj(self, attrib):
      """
      Returns the attribute object matching the specified name.
      
      attrib: (str) The attribute's name.
      """
      if self.has_attribute(attrib):
         attrib_obj = Attribute.objects.filter(object=self).filter(name=attrib)
         return attrib_obj
      else:
         return False
   
   def get_contents(self):
      """
      Returns the contents of an object.
      """
      return list(Object.objects.filter(location__id=self.id).exclude(type__gt=4))
      
   def get_zone(self):
      """
      Returns the object that is marked as this object's zone.
      """
      return self.zone
   
   def move_to(self, target):
      """
      Moves the object to a new location.
      
      target: (Object) Reference to the object to move to.
      """
      self.location = target
      self.save()
      
   def dbref_match(self, oname):
      """
      Check if the input (oname) can be used to identify this particular object
      by means of a dbref match.
      
      oname: (str) Name to match against.
      """
      if not functions_db.is_dbref(oname):
         return False
         
      try:
         is_match = int(oname[1:]) == self.id
      except ValueError:
         return False
         
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
      
      oname: (str) The string to filter from.
      """
      contents = self.get_contents()
      return [prospect for prospect in contents if prospect.name_match(oname)]

   # Type comparison methods.
   def is_player(self):
      return self.type == 1
   def is_room(self):   
      return self.type == 2
   def is_thing(self):
      return self.type == 3
   def is_exit(self):
      return self.type == 4
   def is_going(self):
      return self.type == 5
   def is_garbage(self):
      return self.type == 6
   
   def get_type(self, return_number=False):
      """
      Returns the numerical or string representation of an object's type.
      
      return_number: (bool) True returns numeric type, False returns string.
      """
      if return_number:
         return self.type
      else:
         return global_defines.OBJECT_TYPES[self.type][1]
    
   def is_type(self, otype):
      """
      See if an object is a certain type.
      
      otype: (str) A string representation of the object's type (ROOM, THING)
      """
      otype = otype[0]
      
      if otype == 'p':
         return self.is_player()
      elif otype == 'r':
         return self.is_room()
      elif otype == 't':
         return self.is_thing()
      elif otype == 'e':
         return self.is_exit()
      elif otype == 'g':
         return self.is_garbage()

   def flag_string(self):
      """
      Returns the flag string for an object. This abbreviates all of the flags
      set on the object into a list of single-character flag characters.
      """
      # TODO: Once we add a flag system, add the other flag types here.
      type_string = global_defines.OBJECT_TYPES[self.type][1][0]
      return type_string

   def __str__(self):
      return "%s(#%d%s)" % (self.name, self.id, self.flag_string())

import functions_db
