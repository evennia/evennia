import re

from django.db import models
from django.contrib.auth.models import User, Group

from apps.config.models import ConfigValue
from apps.objects.util import object as util_object
from apps.objects.managers.commchannel import CommChannelManager
from apps.objects.managers.object import ObjectManager
from apps.objects.managers.attribute import AttributeManager
from src import scripthandler
from src import defines_global
from src import ansi
from src import session_mgr
# Import as the absolute path to avoid local variable clashes.
import src.flags
from src.util import functions_general

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
    attr_value = models.CharField(max_length=255)
    attr_hidden = models.BooleanField(default=0)
    attr_object = models.ForeignKey("Object")
    
    objects = AttributeManager()
    
    def __str__(self):
        return "%s(%s)" % (self.attr_name, self.id)
    
    class Admin:
        list_display = ('attr_object', 'attr_name', 'attr_value',)
        search_fields = ['attr_name']
        
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
        return self.attr_value
    
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
        if self.get_name().upper() in defines_global.NOSET_ATTRIBS:
            return True
        else:
            return False
        
    def get_attrline(self):
        """
        Best described as a __str__ method for in-game. Renders the attribute's
        name and value as per MUX.
        """
        return "%s%s%s: %s" % (ansi.ansi["hilite"], 
            self.get_name(), 
            ansi.ansi["normal"], 
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
    home = models.ForeignKey('self', related_name="obj_home", blank=True, null=True)
    type = models.SmallIntegerField(choices=defines_global.OBJECT_TYPES)
    # TODO: Move description to an attribute.s
    description = models.TextField(blank=True, null=True)
    location = models.ForeignKey('self', related_name="obj_location", blank=True, null=True)
    flags = models.TextField(blank=True, null=True)
    nosave_flags = models.TextField(blank=True, null=True)
    date_created = models.DateField(editable=False, auto_now_add=True)
    scriptlink = None
    
    objects = ObjectManager()

    def __cmp__(self, other):
        """
        Used to figure out if one object is the same as another.
        """
        return self.id == other.id

    def __str__(self):
        return "%s" % (self.get_name(no_ansi=True),)
    
    class Meta:
        ordering = ['-date_created', 'id']
    
    class Admin:
        list_display = ('id', 'name', 'type', 'date_created')
        list_filter = ('type',)
        search_fields = ['name']
        save_on_top = True
    
    """
    BEGIN COMMON METHODS
    """
    def get_session(self):
        """
        Returns the session object for a player, or None if none exists.
        """
        if self.is_player():
            return session_mgr.session_from_object(self)
        else:
            return None
        
    def emit_to(self, message):
        """
        Emits something to any sessions attached to the object.
        
        message: (str) The message to send
        """
        # We won't allow emitting to objects... yet.
        if not self.is_player():
            return False
            
        session = self.get_session()
        if session:
            session.msg(ansi.parse_ansi(message))
        else:
            return False
            
    def emit_to_contents(self, message, exclude=None):
        """
        Emits something to all objects inside an object.
        """
        contents = self.get_contents()

        if exclude:
            contents.remove(exclude)
            
        for obj in contents:
            obj.emit_to(message)
    
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

    def user_has_perm(self, perm):
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

    def user_has_perm_list(self, perm_list):
        """
        Checks to see whether a user has the specified permission or is a super
        user. This form accepts an iterable of strings representing permissions,
        if the user has any of them return true.

        perm: (iterable) An iterable of strings of permissions.
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

    def controls_other(self, other_obj):
        """
        See if the envoked object controls another object.
        other_obj: (Object) Reference for object to check dominance of.
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

        # They've failed to meet any of the above conditions.
        return False

    def set_home(self, new_home):
        """
        Sets an object's home.
        """
        self.home = new_home
        self.save()

    def set_name(self, new_name):
        """
        Rename an object.
        """
        self.name = ansi.parse_ansi(new_name, strip_ansi=True)
        self.ansi_name = ansi.parse_ansi(new_name, strip_formatting=True)
        self.save()
        
        # If it's a player, we need to update their user object as well.
        if self.is_player():
            pobject = self.get_user_account()
            pobject.username = new_name
            pobject.save()
            
    def get_user_account(self):
        """
        Returns the player object's account object (User object).
        """
        if not self.is_player():
            return False
        return User.objects.get(id=self.id)

    def get_name(self, fullname=False, show_dbref=True, no_ansi=False):
        """
        Returns an object's name.
        """
        if not no_ansi and self.ansi_name:
            name_string = self.ansi_name
        else:
            name_string = self.name
            
        if show_dbref:
            dbref_string = "(#%s%s)" % (self.id, self.flag_string())
        else:
            dbref_string = ""
        
        if fullname:
            return "%s%s" % (ansi.parse_ansi(name_string, strip_ansi=no_ansi), dbref_string)
        else:
            return "%s%s" % (ansi.parse_ansi(name_string.split(';')[0], strip_ansi=no_ansi), dbref_string)

    def set_description(self, new_desc):
        """
        Set an objects description
        """
        if new_desc == '':
            self.description = None
        else:
            self.description = new_desc
        self.save()

    def get_description(self, no_parsing=False, wrap_text=False):
        """
        Returns an object's ANSI'd description or None if description is not
        set.
        """
        try:
            # If no description is set, return None
            if self.description is None:
                return None
            # Evaluate ANSI and stuff?
            if no_parsing:
                retval = self.description
            else:
                retval = ansi.parse_ansi(self.description)        

            # Default to a 78 character wrap.
            if wrap_text:
                return functions_general.word_wrap(retval)
            else:
                return retval
        except:
            # No description attribute present, return empty string.
            return None
    
    def get_flags(self):
        """
        Returns an object's flag list.
        """
        flags = self.flags
        nosave_flags = self.nosave_flags
        if not flags:
            flags = ""
        if not nosave_flags:
            nosave_flags = ""
            
        return '%s %s' % (flags, nosave_flags)
        
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
    
    def destroy(self):    
        """
        Destroys an object, sets it to GOING. Can still be recovered
        if the user decides to.
        """
        
        # See if we need to kick the player off.
        session = self.get_session()
        if session:
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
        self.type = 5
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
        self.type = 6
        self.save()

        # Clear all attributes
        self.clear_all_attributes()

    def clear_exits(self):
        """
        Destroys all of the exits and any exits pointing to this
        object as a destination.
        """
        exits = self.get_contents(filter_type=4)
        exits += self.obj_home.all().filter(type__exact=4)

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
                functions_general.log_errmsg("Missing default home, %s '%s(#%d)' now has a null location." % (text, obj.name, obj.id))
                    
            if obj.is_player():
                if obj.is_connected_plr():
                    if home:
                        obj.emit_to("Your current location has ceased to exist, moving you to your home %s(#%d)." % (home.name, home.id))
                    else:
                        # Famous last words: The player should never see this.
                        obj.emit_to("You seem to have found a place that does not exist.")
                    
            # If home is still None, it goes to a null location.
            obj.move_to(home, True)
            obj.save()

    def set_attribute(self, attribute, new_value):
        """
        Sets an attribute on an object. Creates the attribute if need
        be.
        
        attribute: (str) The attribute's name.
        new_value: (str) The value to set the attribute to.
        """
        if self.has_attribute(attribute):
            # Attribute already exists, update it.
            attrib_obj = Attribute.objects.filter(attr_object=self).filter(attr_name__iexact=attribute)[0]
            attrib_obj.attr_value = new_value
            attrib_obj.save()
        else:
            # Attribute object doesn't exist, create it.
            new_attrib = Attribute()
            new_attrib.attr_name = attribute
            new_attrib.attr_value = new_value
            new_attrib.attr_object = self
            new_attrib.attr_hidden = False
            new_attrib.save()
            
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
        match_exp = re.compile(functions_general.wildcard_to_regexp(searchstr), re.IGNORECASE)
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
        return flag in flags or flag in nosave_flags
        
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
            # We've already go it.
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
                flags = str(self.flags).split()
                flags.append(flag)
                self.flags = ' '.join(flags)
            self.save()
    
    def is_connected_plr(self):
        """
        Is this object a connected player?
        """
        if self.is_player():
            if self.get_session():
                return True
            else:
                return False
        else:
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
        if not self.scriptlink:
            if self.is_player():
                script_to_load = 'player.basicplayer'
            else:
                script_to_load = 'basicobject'
            self.scriptlink = scripthandler.scriptlink(self, self.get_attribute_value('__parent', script_to_load))
        
        if self.scriptlink:    
            # If the scriptlink variable can't be populated, this will fail
            # silently and let the exception hit in the scripthandler.
            return self.scriptlink
        return None
        
    def get_attribute_value(self, attrib, default=False):
        """
        Returns the value of an attribute on an object. You may need to
        type cast the returned value from this function!
        
        attrib: (str) The attribute's name.
        """
        if self.has_attribute(attrib):
            attrib = Attribute.objects.filter(attr_object=self).filter(attr_name=attrib)
            return attrib[0].attr_value
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
            return Attribute.objects.filter(attr_object=self).filter(attr_name=attrib)
        else:
            return False
    
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
    
    def move_to(self, target, quiet=False):
        """
        Moves the object to a new location.
        
        target: (Object) Reference to the object to move to.
        quiet:  (bool)    If true, don't emit left/arrived messages.
        """
        if not quiet:
            if self.get_location():
                self.get_location().emit_to_contents("%s has left." % (self.get_name(),), exclude=self)
            
        self.location = target
        self.save()
        
        if not quiet:
            self.get_location().emit_to_contents("%s has arrived." % (self.get_name(),), exclude=self)
        
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
        if oname[0] == '#':
            # First character is a pound sign, looks to be a dbref.
            return self.dbref_match(oname)
        elif match_type == "exact":
            # Exact matching
            name_chunks = self.name.lower().split(';')
            for chunk in name_chunks:
                if oname.lower() == chunk:
                    return True
            return False
        else:
            # Fuzzy matching.
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

class CommChannel(models.Model):
    """
    The CommChannel class represents a comsys channel in the vein of MUX/MUSH.
    """
    name = models.CharField(max_length=255)
    ansi_name = models.CharField(max_length=255)
    owner = models.ForeignKey(Object, related_name="chan_owner")
    description = models.CharField(max_length=80)
    req_grp = models.ManyToManyField(Group, blank=True, null=True)
    
    objects = CommChannelManager()

    def __str__(self):
        return "%s" % (self.name,)
    
    class Meta:
        ordering = ['-name']
        permissions = (
            ("emit_commchannel", "May @cemit over channels."),
        )
    
    class Admin:
        list_display = ('name', 'owner')

    def get_name(self):
        """
        Returns a channel's name.
        """
        return self.name

    def get_header(self):
        """
        Returns the channel's header text, or what is shown before each channel
        message.
        """
        return ansi.parse_ansi(self.ansi_name)

    def get_owner(self):
        """
        Returns a channels' owner.
        """
        return self.owner

    def set_name(self, new_name):
        """
        Rename a channel
        """
        self.name = ansi.parse_ansi(new_name, strip_ansi=True)
        self.header = "[%s]" % (ansi.parse_ansi(new_name),)
        self.save()

    def set_header(self, new_header):
        """
        Sets a channel's header text.
        """
        self.header = ansi.parse_ansi(new_header)
        self.save()

    def set_owner(self, new_owner):
        """
        Sets a channel's owner.
        """
        self.owner = new_owner
        self.save()

class CommChannelMessage(models.Model):
    """
    A single logged channel message.
    """
    channel = models.ForeignKey(CommChannel, related_name="msg_channel")
    message = models.CharField(max_length=255)
    date_sent = models.DateTimeField(editable=False, auto_now_add=True)
    
    objects = CommChannelManager()

    def __str__(self):
        return "%s: %s" % (self.sender.name, self.message)
    
    class Meta:
        ordering = ['-date_sent']
    
    class Admin:
        list_display = ('channel', 'message')
