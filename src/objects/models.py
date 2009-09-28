"""
This is where all of the crucial, core object models reside. 
"""
import re

try: import cPickle as pickle
except ImportError: import pickle

from django.db import models
from django.contrib.auth.models import User, Group
from django.conf import settings
from src.objects.util import object as util_object
from src.objects.managers.object import ObjectManager
from src.objects.managers.attribute import AttributeManager
from src.config.models import ConfigValue
from src.ansi import ANSITable, parse_ansi
from src import scripthandler
from src import defines_global
from src import session_mgr
from src import logger

# Import as the absolute path to avoid local variable clashes.
import src.flags
from src.util import functions_general

from src.logger import log_infomsg

class Attribute(models.Model):
    """
    Attributes are things that are specific to different types of objects. For
    example, a drink container needs to store its fill level, whereas an exit
    needs to store its open/closed/locked/unlocked state. These are done via
    attributes, rather than making different classes for each object type and
    storing them directly. The added benefit is that we can add/remove 
    attributes on the fly as we like.
    """
    attr_name = models.CharField(max_length=255)
    attr_value = models.TextField(blank=True, null=True)
    attr_hidden = models.BooleanField(default=False)
    attr_object = models.ForeignKey("Object")
    attr_ispickled = models.BooleanField(default=False)
    
    objects = AttributeManager()
    
    def __str__(self):
        return "%s(%s)" % (self.attr_name, self.id)
            
    """
    BEGIN COMMON METHODS
    """
    def get_name(self):
        """
        Returns an attribute's name.
        """
        return self.attr_name
        
    def get_value(self):
        """
        Returns an attribute's value.
        """        
        attr_value = str(self.attr_value)        
        if self.attr_ispickled:
            attr_value = pickle.loads(attr_value)                        
        return attr_value
    
    def get_object(self):
        """
        Returns the object that the attribute resides on.
        """
        return self.attr_object
        
    def is_hidden(self):
        """
        Returns True if the attribute is hidden.
        """
        if self.attr_hidden or self.get_name().upper() in defines_global.HIDDEN_ATTRIBS:
            return True
        else:
            return False

    def is_noset(self):
        """
        Returns True if the attribute is unsettable.
        """
        if self.get_name().upper() in defines_global.NOSET_ATTRIBS:            return True
        else:
            return False
        
    def get_attrline(self):
        """
        Best described as a __str__ method for in-game. Renders the attribute's
        name and value as per MUX.
        """
        
        return "%s%s%s: %s" % (ANSITable.ansi["hilite"], 
                               self.get_name(),ANSITable.ansi["normal"],
                               self.get_value())

class Object(models.Model):
    """
    The Object class is very generic representation of a THING, PLAYER, EXIT,
    ROOM, or other entities within the database. Pretty much anything in the
    game is an object. Objects may be one of several different types, and
    may be parented to allow for differing behaviors.
    
    We eventually want to find some way to implement object parents via loadable 
    modules or sub-classing.
    """
    name = models.CharField(max_length=255)
    ansi_name = models.CharField(max_length=255)
    owner = models.ForeignKey('self', related_name="obj_owner", blank=True, null=True)
    zone = models.ForeignKey('self', related_name="obj_zone", blank=True, null=True)
    script_parent = models.CharField(max_length=255, blank=True, null=True)
    home = models.ForeignKey('self', related_name="obj_home", blank=True, null=True)
    type = models.SmallIntegerField(choices=defines_global.OBJECT_TYPES)
    location = models.ForeignKey('self', related_name="obj_location", blank=True, null=True)
    flags = models.TextField(blank=True, null=True)
    nosave_flags = models.TextField(blank=True, null=True)
    date_created = models.DateField(editable=False, auto_now_add=True)

    # 'scriptlink' is a 'get' property for retrieving a reference to the correct
    # script object. Defined down by get_scriptlink()
    scriptlink_cached = None
    
    objects = ObjectManager()

    #state system can set a particular command table to be used (not persistent).
    state = None

    def __cmp__(self, other):
        """
        Used to figure out if one object is the same as another.
        """
        return self.id == other.id

    def __str__(self):
        return "%s" % (self.get_name(no_ansi=True),)
    
    class Meta:
        ordering = ['-date_created', 'id']

    def dbref(self):
        """Returns the object's dbref id on the form #NN, directly
        usable by Object.objects.dbref_search()
        """
        return "#%s" % str(self.id)
        
    """
    BEGIN COMMON METHODS
    """
    def search_for_object(self, ostring, emit_to_obj=None, search_contents=True, 
                                search_location=True, dbref_only=False, 
                                limit_types=False, search_aliases=False,
                                attribute_name=None):
        """
        Perform a standard object search, handling multiple
        results and lack thereof gracefully.

        ostring: (str) The string to match object names against.
                       Obs - To find a player, append * to the start of ostring. 
        emit_to_obj: (obj) An object (instead of caller) to receive search feedback
        search_contents: (bool) Search the caller's inventory
        search_location: (bool) Search the caller's location
        dbref_only: (bool) Requires ostring to be a #dbref
        limit_types: (list) Object identifiers from defines_global.OTYPE:s
        search_aliases: (bool) Search player aliases first
        attribute_name: (string) Which attribute to match (if None, uses default 'name')
        """

        # This is the object that gets the duplicate/no match emits.
        if not emit_to_obj:
            emit_to_obj = self
            
        if search_aliases:
            # If an alias match is found, get out of here and skip the rest.
            alias_results = Object.objects.player_alias_search(self, ostring)
            if alias_results:
                return alias_results[0]
            
        results = Object.objects.local_and_global_search(self, ostring, 
                                search_contents=search_contents, 
                                search_location=search_location, 
                                dbref_only=dbref_only, 
                                limit_types=limit_types,
                                attribute_name=attribute_name)

        if len(results) > 1:
            s = "More than one match for '%s' (please narrow target):" % ostring            
            for num, result in enumerate(results):
                invtext = ""
                if result.get_location() == self:
                    invtext = " (carried)"                    
                s += "\n %i-%s%s" % (num+1, result.get_name(show_dbref=False),invtext)
            emit_to_obj.emit_to(s)            
            return False
        elif len(results) == 0:
            emit_to_obj.emit_to("I don't see that here.")
            return False
        else:
            return results[0]
        
    def get_sessions(self):
        """
        Returns a list of sessions matching this object.
        """
        if self.is_player():
            return session_mgr.sessions_from_object(self)
        else:
            return []
        
    def emit_to(self, message):
        """
        Emits something to any sessions attached to the object.
        
        message: (str) The message to send
        """
        # We won't allow emitting to objects... yet.
        if not self.is_player():
            return False
            
        sessions = self.get_sessions()
        for session in sessions:
            session.msg(parse_ansi(message))
            
    def execute_cmd(self, command_str, session=None):
        """
        Do something as this object.
        """      
        # The Command object has all of the methods for parsing and preparing
        # for searching and execution. Send it to the handler once populated.
        cmdhandler.handle(cmdhandler.Command(self, command_str, session=session))
            
    def emit_to_contents(self, message, exclude=None):
        """
        Emits something to all objects inside an object.
        """
        contents = self.get_contents()

        if exclude:
            try:
                contents.remove(exclude)
            except ValueError:
                # Sometimes very weird things happen with locations, fail
                # silently.
                pass
            
        for obj in contents:
            obj.emit_to(message)
            
    def get_user_account(self):
        """
        Returns the player object's account object (User object).
        """
        try:
            return User.objects.get(id=self.id)
        except User.DoesNotExist:
            logger.log_errmsg("No account match for object id: %s" % self.id)
            return None
    
    def is_staff(self):
        """
        Returns True if the object is a staff player.
        """
        if not self.is_player():
            return False        
        try:
            profile = self.get_user_account()
            return profile.is_staff
        except User.DoesNotExist:
            return False

    def is_superuser(self):
        """
        Returns True if the object is a super user player.
        """
        if not self.is_player():
            return False
        
        try:
            profile = self.get_user_account()
            return profile.is_superuser
        except User.DoesNotExist:
            return False
        
    def sees_dbrefs(self):
        """
        Returns True if the object sees dbrefs in messages. This is here
        instead of session.py due to potential future expansion in the
        direction of MUX-style puppets.
        """
        looker_user = self.get_user_account()
        if looker_user:
            # Builders see dbrefs
            return looker_user.has_perm('genperms.builder')
        else:
            return False

    def has_perm(self, perm):
        """
        Checks to see whether a user has the specified permission or is a super
        user.

        perm: (string) A string representing the desired permission.
        """
        if not self.is_player():
            return False

        if self.is_superuser():
            return True

        if self.get_user_account().has_perm(perm):
            return True
        else:
            return False

    def has_perm_list(self, perm_list):
        """
        Checks to see whether a user has the specified permission or is a super
        user. This form accepts an iterable of strings representing permissions,
        if the user has any of them return true.

        perm_list: (iterable) An iterable of strings of permissions.
        """
        if not self.is_player():
            return False

        if self.is_superuser():
            return True

        for perm in perm_list:
            # Stop searching perms on the first match.
            if self.get_user_account().has_perm(perm):
                return True
            
        # Fall through to failure
        return False

    def owns_other(self, other_obj):
        """
        See if the envoked object owns another object.
        other_obj: (Object) Reference for object to check ownership of.
        """
        return self.id == other_obj.get_owner().id

    def controls_other(self, other_obj, builder_override=False):
        """
        See if the envoked object controls another object.
        other_obj: (Object) Reference for object to check dominance of.
        builder_override: (bool) True if builder perm allows controllership.
        """
        if self == other_obj:
            return True
            
        if self.is_superuser():
            # Don't allow superusers to dominate other superusers.
            if not other_obj.is_superuser():
                return True
            else:
                return False
        
        if self.owns_other(other_obj):
            # If said object owns the target, then give it the green.
            return True
        
        # When builder_override is enabled, a builder permission means
        # the object controls the other.
        if builder_override and not other_obj.is_player() and self.has_perm('genperms.builder'):
            return True

        # They've failed to meet any of the above conditions.
        return False

    def set_home(self, new_home):
        """
        Sets an object's home.
        """
        self.home = new_home
        self.save()
        
    def set_owner(self, new_owner):
        """
        Sets an object's owner.
        """
        self.owner = new_owner
        self.save()

    def set_name(self, new_name):
        """
        Rename an object.
        """
        self.name = parse_ansi(new_name, strip_ansi=True)
        self.ansi_name = parse_ansi(new_name, strip_formatting=True)
        self.save()
        
        # If it's a player, we need to update their user object as well.
        if self.is_player():
            pobject = self.get_user_account()
            pobject.username = new_name
            pobject.save()

    def get_name(self, fullname=False, show_dbref=True, show_flags=True, 
                                                        no_ansi=False):
        """
        Returns an object's name.
        """
        if not no_ansi and self.ansi_name:
            name_string = self.ansi_name
        else:
            name_string = self.name
            
        if show_dbref:
            # Allow hiding of the flags but show the dbref.
            if show_flags:
                flag_string = self.flag_string()
            else:
                flag_string = ""

            dbref_string = "(#%s%s)" % (self.id, flag_string)
        else:
            dbref_string = ""
        
        if fullname:
            return "%s%s" % (parse_ansi(name_string, strip_ansi=no_ansi), 
                             dbref_string)
        else:
            return "%s%s" % (parse_ansi(name_string.split(';')[0], 
                                             strip_ansi=no_ansi), dbref_string)
    
    def destroy(self):    
        """
        Destroys an object, sets it to GOING. Can still be recovered
        if the user decides to.
        """
        
        # See if we need to kick the player off.
        sessions = self.get_sessions()
        for session in sessions:
            session.msg("You have been destroyed, goodbye.")
            session.handle_close()
            
        # If the object is a player, set the player account object to inactive.
        # It can still be recovered at this point.        
        if self.is_player():
            try:
                uobj = User.objects.get(id=self.id)
                uobj.is_active = False
                uobj.save()
            except:
                functions_general.log_errmsg('Destroying object %s but no matching player.' % (self,))

        # Set the object type to GOING
        self.type = defines_global.OTYPE_GOING                
        # Destroy any exits to and from this room, do this first
        self.clear_exits()
        # Clear out any objects located within the object
        self.clear_objects()
        self.save()
              
    def delete(self):
        """
        Deletes an object permanently. Marks it for re-use by a new object.
        """
        # Delete the associated player object permanently.
        uobj = User.objects.filter(id=self.id)
        if len(uobj) > 0:
            uobj[0].delete()
            
        # Set the object to type GARBAGE.
        self.type = defines_global.OTYPE_GARBAGE
        self.save()

        # Clear all attributes & flags
        self.clear_all_attributes()
        self.clear_all_flags()

    def clear_exits(self):
        """
        Destroys all of the exits and any exits pointing to this
        object as a destination.
        """
        exits = self.get_contents(filter_type=defines_global.OTYPE_EXIT)
        exits += self.obj_home.all().filter(type__exact=defines_global.OTYPE_EXIT)

        for exit in exits:
            exit.destroy()

    def clear_objects(self):
        """
        Moves all objects (players/things) currently in a GOING -> GARBAGE location
        to their home or default home (if it can be found).
        """
        # Gather up everything, other than exits and going/garbage, that is under
        # the belief this is its location.
        objs = self.obj_location.filter(type__in=[1,2,3])
        default_home_id = ConfigValue.objects.get_configvalue('default_home')
        try:
            default_home = Object.objects.get(id=default_home_id)
        except:
            functions_general.log_errmsg("Could not find default home '(#%d)'." % (default_home_id))

        for obj in objs:
            home = obj.get_home()
            text = "object"

            if obj.is_player():
                text = "player"

            # Obviously, we can't send it back to here.
            if home.id == self.id:
                obj.home = default_home
                obj.save()
                home = default_home

            # If for some reason it's still None...
            if not home:
                functions_general.log_errmsg("Missing default home, %s '%s(#%d)' now has a null location." %
                                             (text, obj.name, obj.id))
                    
            if obj.is_player():
                if obj.is_connected_plr():
                    if home:
                        obj.emit_to("Your current location has ceased to exist, moving you to your home %s(#%d)." %
                                    (home.name, home.id))
                    else:
                        # Famous last words: The player should never see this.
                        obj.emit_to("You seem to have found a place that does not exist ...")
                    
            # If home is still None, it goes to a null location.            
            obj.move_to(home)
            obj.save()



    def set_attribute(self, attribute, new_value=None):
        """
        Sets an attribute on an object. Creates the attribute if need
        be.
        
        attribute: (str) The attribute's name.
        new_value: (python obj) The value to set the attribute to. If this is not
                                a str, the object will be stored as a pickle.  
        """

        attrib_obj = None
        if self.has_attribute(attribute):
            attrib_obj = \
              Attribute.objects.filter(attr_object=self).filter(attr_name__iexact=attribute)[0]
                    
        if new_value != None:
            #pickle if anything else than str
            if type(new_value) != type(str()):
                new_value = pickle.dumps(new_value)#,pickle.HIGHEST_PROTOCOL)
                ispickled = True
            else:
                new_value = new_value
                ispickled = False

            if attrib_obj:                
                # Save over the existing attribute's value.
                attrib_obj.attr_value = new_value
                attrib_obj.attr_ispickled = ispickled
                attrib_obj.save()
            else:
                # Create a new attribute
                new_attrib = Attribute()
                new_attrib.attr_name = attribute
                new_attrib.attr_value = new_value
                new_attrib.attr_object = self
                new_attrib.attr_hidden = False
                new_attrib.attr_ispickled = ispickled
                new_attrib.save()

        elif attrib_obj:
            # If you do something like @set me=attrib: , destroy the attrib.   
            attrib_obj.delete()
                            

    def get_attribute_value(self, attrib, default=None):
        """
        Returns the value of an attribute on an object. You may need to
        type cast the returned value from this function since the attribute
        can be of any type.
        
        attrib: (str) The attribute's name.
        """
        if self.has_attribute(attrib):            
            attrib = Attribute.objects.filter(attr_object=self).filter(attr_name=attrib)[0]
            return attrib.get_value()
        else:            
            return default
            

    def get_attribute_obj(self, attrib):
        """
        Returns the attribute object matching the specified name.
        
        attrib: (str) The attribute's name.
        """
        if self.has_attribute(attrib):
            return Attribute.objects.filter(attr_object=self).filter(attr_name=attrib)
        else:
            return False


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
            

    def get_all_attributes(self):
        """
        Returns a QuerySet of an object's attributes.
        """
        return [attr for attr in self.attribute_set.all() if not attr.is_hidden()]
        

    def clear_all_attributes(self):
        """
        Clears all of an object's attributes.
        """
        attribs = self.get_all_attributes()
        for attrib in attribs:
            attrib.delete()


    def has_attribute(self, attribute):
        """
        See if we have an attribute set on the object.
        
        attribute: (str) The attribute's name.
        """
        attr = Attribute.objects.filter(attr_object=self).filter(attr_name__iexact=attribute)
        if attr.count() == 0:
            return False
        else:
            return True
            

    def attribute_namesearch(self, searchstr, exclude_noset=False):
        """
        Searches the object's attributes for name matches against searchstr
        via regular expressions. Returns a list.
        
        searchstr: (str) A string (maybe with wildcards) to search for.
        """
        # Retrieve the list of attributes for this object.
        attrs = Attribute.objects.filter(attr_object=self)
        # Compile a regular expression that is converted from the user's
        # wild-carded search string.
        match_exp = re.compile(functions_general.wildcard_to_regexp(searchstr), 
                               re.IGNORECASE)
        # If the regular expression search returns a match object, add to results.
        if exclude_noset:
            return [attr for attr in attrs if match_exp.search(attr.get_name()) and not attr.is_hidden() and not attr.is_noset()]
        else:
            return [attr for attr in attrs if match_exp.search(attr.get_name()) and not attr.is_hidden()]
        

    def has_flag(self, flag):
        """
        Does our object have a certain flag?
        
        flag: (str) Flag name
        """
        # For whatever reason, we have to do this so things work
        # in SQLite.
        flags = str(self.flags).split()
        nosave_flags = str(self.nosave_flags).split()
        return flag.upper() in flags or flag in nosave_flags
        
    def set_flag(self, flag, value=True):
        """
        Add a flag to our object's flag list.
        
        flag: (str) Flag name
        value: (bool) Set (True) or un-set (False)
        """
        flag = flag.upper()
        has_flag = self.has_flag(flag)
        
        if value == False and has_flag:
            # Clear the flag.
            if src.flags.is_unsavable_flag(flag):
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
            # We've already got it.
            pass
        else:
            # Setting a flag.
            if src.flags.is_unsavable_flag(flag):
                # Not a savable flag (CONNECTED, etc)
                flags = str(self.nosave_flags).split()
                flags.append(flag)
                self.nosave_flags = ' '.join(flags)
            else:
                # Is a savable flag.
                if self.flags is not None:
                    flags = str(self.flags).split()
                else:
                    # This prevents conversion of None to strings
                    flags = []

                flags.append(flag)
                self.flags = ' '.join(flags)
            self.save()

    def unset_flag(self, flag):
        self.set_flag(flag,value=False)
    
    def get_flags(self):
        """
        Returns an object's flag list.
        """
        all_flags = []
        if self.flags is not None:
            # Add saved flags to the display list
            all_flags = all_flags + self.flags.split()
        if self.nosave_flags is not None:
            # Add non-saved flags to the display list
            all_flags = all_flags + self.nosave_flags.split()
            
        if not all_flags:
            # Guard against returning 'None'
            return ""
        else:
            # Format the Python list to a space separated string of flags
            return " ".join(all_flags)

    def clear_all_flags(self):
        "Clears all the flags set on object."
        flags = self.get_flags()
        for flag in flags.split():
            self.unset_flag(flag)

    def is_connected_plr(self):
        """
        Is this object a connected player?
        """
        if self.is_player():
            if self.get_sessions():
                return True

        # No matches or not a player
        return False
        
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
        try:
            return self.home
        except:
            return None
    
    def get_location(self):
        """
        Returns an object's location.
        """
        try:
            return self.location
        except:
            functions_general.log_errmsg("Object '%s(#%d)' has invalid location: #%s" % (self.name,self.id,self.location_id))
            return False
            
    def get_scriptlink(self):
        """
        Returns an object's script parent.
        """
        if not self.scriptlink_cached:
            script_to_load = self.get_script_parent()
            
            # Load the script reference into the object's attribute.
            self.scriptlink_cached = scripthandler.scriptlink(self, 
                                                            script_to_load)        
        if self.scriptlink_cached:    
            # If the scriptlink variable can't be populated, this will fail
            # silently and let the exception hit in the scripthandler.
            return self.scriptlink_cached
        return None
    # Set a property to make accessing the scriptlink more transparent.
    scriptlink = property(fget=get_scriptlink)
    
    def get_script_parent(self):
        """
        Returns a string representing the object's script parent.
        """
        if not self.script_parent or self.script_parent.strip() == '':
            # No parent value, assume the defaults based on type.
            if self.is_player():
                return settings.SCRIPT_DEFAULT_PLAYER
            else:
                return settings.SCRIPT_DEFAULT_OBJECT
        else:
            # A parent has been set, load it from the field's value.
            return self.script_parent
    
    def set_script_parent(self, script_parent=None):
        """
        Sets the object's script_parent attribute and does any logistics.
        
        script_parent: (string) String pythonic import path of the script parent
                                assuming the python path is game/gamesrc/parents. 
        """        
        if script_parent != None and scripthandler.scriptlink(self, str(script_parent).strip()):
            #assigning a custom parent 
            self.script_parent = str(script_parent).strip()
            self.save()
            return            
        #use a default parent instead
        if self.is_player():
            self.script_parent = settings.SCRIPT_DEFAULT_PLAYER
        else:
            self.script_parent = settings.SCRIPT_DEFAULT_OBJECT                                        
        self.save()
    
    def get_contents(self, filter_type=None):
        """
        Returns the contents of an object.
        
        filter_type: (int) An object type number to filter by.
        """
        if filter_type:
            return list(Object.objects.filter(location__id=self.id).filter(type=filter_type))
        else:
            return list(Object.objects.filter(location__id=self.id).exclude(type__gt=4))
        
    def get_zone(self):
        """
        Returns the object that is marked as this object's zone.
        """
        try:
            return self.zone
        except:
            return None

    def set_zone(self, new_zone):
        """
        Sets an object's zone.
        """
        self.zone = new_zone
        self.save()
    
    def move_to(self, target, quiet=False, force_look=True):
        """
        Moves the object to a new location.
        
        target: (Object) Reference to the object to move to.
        quiet:  (bool)    If true, don't emit left/arrived messages.
        force_look: (bool) If true and self is a player, make them 'look'.
        """
        
        #before the move, call eventual pre-commands.
        if self.scriptlink.at_before_move(target) != None:
            return 

        if not quiet:
            #tell the old room we are leaving
            self.scriptlink.announce_move_from(target)
            source_location = self.location
            
        #perform move
        self.location = target
        self.save()        
                
        if not quiet:
            #tell the new room we are there. 
            self.scriptlink.announce_move_to(source_location)

        #execute eventual extra commands on this object after moving it
        self.scriptlink.at_after_move()
                                
        if force_look and self.is_player():
            self.execute_cmd('look')
        

    def dbref_match(self, oname):
        """
        Check if the input (oname) can be used to identify this particular object
        by means of a dbref match.
        
        oname: (str) Name to match against.
        """
        if not util_object.is_dbref(oname):
            return False
            
        try:
            is_match = int(oname[1:]) == self.id
        except ValueError:
            return False
            
        return is_match
        
    def name_match(self, oname, match_type="fuzzy"):
        """    
        See if the input (oname) can be used to identify this particular object.
        Check the # sign for dbref (exact) reference, and anything else is a
        name comparison.
        
        NOTE: A 'name' can be a dbref or the actual name of the object. See
        dbref_match for an exclusively name-based match.
        """
        
        if util_object.is_dbref(oname):
            # First character is a pound sign, looks to be a dbref.
            return self.dbref_match(oname)

        oname = oname.lower()
        if match_type == "exact":
            #exact matching
            name_chunks = self.name.lower().split(';')
            #False=0 and True=1 in python, so if sum>0, we
            #have at least one exact match.
            return sum(map(lambda o: oname == o, name_chunks)) > 0
        else:
            #fuzzy matching
            return oname in self.name.lower()
            
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
        return self.type == defines_global.OTYPE_PLAYER
    def is_room(self):    
        return self.type == defines_global.OTYPE_ROOM
    def is_thing(self):
        return self.type == defines_global.OTYPE_THING
    def is_exit(self):
        return self.type == defines_global.OTYPE_EXIT
    def is_going(self):
        return self.type == defines_global.OTYPE_GOING
    def is_garbage(self):
        return self.type == defines_global.OTYPE_GARBAGE
    
    def get_type(self, return_number=False):
        """
        Returns the numerical or string representation of an object's type.
        
        return_number: (bool) True returns numeric type, False returns string.
        """
        if return_number:
            return self.type
        else:
            return defines_global.OBJECT_TYPES[self.type][1]
     
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
        # We have to cast this because the admin interface is really picky
        # about tuple index types. Bleh.
        otype = int(self.type)
        return defines_global.OBJECT_TYPES[otype][1][0]

    #state access functions

    def get_state(self):        
        return self.state
    
    def set_state(self, state_name=None):
        """
        Only allow setting a state on a player object, otherwise
        fail silently.
        """
        if self.is_player():            
            self.state = state_name      

    def clear_state(self):
        "Set to no state (return to normal operation)"
        self.state = None

    def purge_object(self):
        "Completely clears all aspects of the object."
        self.clear_all_attributes()
        self.clear_all_flags()
        self.clear_state()


# Deferred imports are poopy. This will require some thought to fix.
from src import cmdhandler
