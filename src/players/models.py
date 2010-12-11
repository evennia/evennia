"""
Player

The Player class is a simple extension of the django User model using
the 'profile' system of django. A profile is a model that tack new
fields to the User model without actually editing the User model
(which would mean hacking into django internals which we want to avoid
for future compatability reasons).  The profile, which we call
'Player', is accessed with user.get_profile() by the property 'player'
defined on ObjectDB objects. Since we can customize it, we will try to
abstract as many operations as possible to work on Player rather than
on User.

We use the Player to store a more mud-friendly style of permission
system as well as to allow the admin more flexibility by storing
attributes on the Player.  Within the game we should normally use the
Player manager's methods to create users, since that automatically
adds the profile extension.

The default Django permission system is geared towards web-use, and is
defined on a per-application basis permissions. In django terms,
'src/objects' is one application, 'src/scripts' another, indeed all
folders in /src with a model.py inside them is an application. Django
permissions thus have the form
e.g. 'applicationlabel.permissionstring' and django automatically
defines a set of these for editing each application from its automatic
admin interface. These are still available should you want them.

For most in-game mud-use however, like commands and other things, it
does not make sense to tie permissions to the applications in src/ -
To the user these should all just be considered part of the game
engine. So instead we define our own separate permission system here,
borrowing heavily from the django original, but allowing the
permission string to look however we want, making them unrelated to
the applications.

To make the Player model more flexible for your own game, it can also
persistently store attributes of its own. This is ideal for extra
account info and OOC account configuration variables etc.

"""

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils.encoding import smart_str
from src.server.sessionhandler import SESSIONS
from src.players import manager 
from src.typeclasses.models import Attribute, TypedObject
from src.permissions import permissions
from src.utils import logger

#------------------------------------------------------------
#
# PlayerAttribute
#
#------------------------------------------------------------

class PlayerAttribute(Attribute):
    """
    PlayerAttributes work the same way as Attributes on game objects,
    but are intended to store OOC information specific to each user
    and game (example would be configurations etc).
    """
    db_obj = models.ForeignKey("PlayerDB")    

    class Meta:
        "Define Django meta options"
        verbose_name = "Player Attribute"
        verbose_name_plural = "Player Attributes"

#------------------------------------------------------------
#
# PlayerDB
#
#------------------------------------------------------------

class PlayerDB(TypedObject):
    """
    This is a special model using Django's 'profile' functionality
    and extends the default Django User model. It is defined as such 
    by use of the variable AUTH_PROFILE_MODULE in the settings. 
    One accesses the fields/methods. We try use this model as much 
    as possible rather than User, since we can customize this to
    our liking. 

    The TypedObject supplies the following (inherited) properties:
      key - main name
      name - alias for key
      typeclass_path - the path to the decorating typeclass
      typeclass - auto-linked typeclass
      date_created - time stamp of object creation
      permissions - perm strings 
      dbref - #id of object 
      db - persistent attribute storage
      ndb - non-persistent attribute storage 

    The PlayerDB adds the following properties: 
      user - Connected User object. django field, needs to be save():d. 
      obj - game object controlled by player
      character - alias for obj 
      name - alias for user.username
      sessions - sessions connected to this player
      is_superuser - bool if this player is a superuser
      
    """
    

    #
    # PlayerDB Database model setup 
    # 
    # inherited fields (from TypedObject): 
    # db_key, db_typeclass_path, db_date_created, db_permissions

    # this is the one-to-one link between the customized Player object and
    # this profile model. It is required by django. 
    user = models.ForeignKey(User, unique=True)
    # the in-game object connected to this player (if any). 
    # Use the property 'obj' to access. 
    db_obj = models.ForeignKey("objects.ObjectDB", null=True)

    # Database manager 
    objects = manager.PlayerManager()

    class Meta:
        app_label = 'players'

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value, 
    # value = self.attr and del self.attr respectively (where self 
    # is the object in question).

    # obj property (wraps db_obj)
    #@property
    def obj_get(self):
        "Getter. Allows for value = self.obj"
        return self.db_obj
    #@obj.setter
    def obj_set(self, value):
        "Setter. Allows for self.obj = value"
        from src.typeclasses.typeclass import TypeClass
        if isinstance(value, TypeClass):
            value = value.dbobj    
        try:
            self.db_obj = value
            self.save()
        except Exception:
            logger.log_trace()
            raise Exception("Cannot assign %s as a player object!" % value)   
    #@obj.deleter
    def obj_del(self):
        "Deleter. Allows for del self.obj"
        self.db_obj = None
        self.save()
    obj = property(obj_get, obj_set, obj_del)

    # whereas the name 'obj' is consistent with the rest of the code, 
    # 'character' is a more intuitive property name, so we 
    # define this too, as an alias to player.obj.
    #@property
    def character_get(self):
        "Getter. Allows for value = self.character"
        return self.obj
    #@character.setter
    def character_set(self, value):
        "Setter. Allows for self.character = value"
        self.obj = value
    #@character.deleter
    def character_del(self):
        "Deleter. Allows for del self.character"
        del self.obj
    character = property(character_get, character_set, character_del)

    class Meta:
        "Define Django meta options"
        verbose_name = "Player"
        verbose_name_plural = "Players"

    #
    # PlayerDB main class properties and methods
    # 

    def __str__(self):
        return smart_str("%s(player %i)" % (self.name, self.id))
        
    def __unicode__(self):
        return u"%s(player#%i)" % (self.name, self.id)

    # this is used by all typedobjects as a fallback
    try:
        default_typeclass_path = settings.BASE_PLAYER_TYPECLASS
    except Exception:
        default_typeclass_path = "src.players.player.Player"

    # this is required to properly handle attributes
    attribute_model_path = "src.players.models"
    attribute_model_name = "PlayerAttribute"

        # name property (wraps self.user.username)
    #@property
    def name_get(self):
        "Getter. Allows for value = self.name"
        return self.user.username
    #@name.setter
    def name_set(self, value):
        "Setter. Allows for player.name = newname"
        self.user.username = value
        self.user.save() # this might be stopped by Django?
    #@name.deleter
    def name_del(self):
        "Deleter. Allows for del self.name"
        raise Exception("Player name cannot be deleted!")
    name = property(name_get, name_set, name_del)
    key = property(name_get, name_set, name_del)

    # sessions property
    #@property
    def sessions_get(self):
        "Getter. Retrieve sessions related to this player/user"
        return SESSIONS.sessions_from_player(self)
    #@sessions.setter
    def sessions_set(self, value):
        "Setter. Protects the sessions property from adding things"
        raise Exception("Cannot set sessions manually!")
    #@sessions.deleter
    def sessions_del(self):
        "Deleter. Protects the sessions property from deletion"
        raise Exception("Cannot delete sessions manually!")        
    sessions = property(sessions_get, sessions_set, sessions_del)

    #@property
    def is_superuser_get(self):
        "Superusers have all permissions."
        return self.user.is_superuser
    is_superuser = property(is_superuser_get)

    def set_perm(self, perm):
        "Shortcuts to set permissions, replacing old ones"
        return permissions.set_perm(self, perm)
    def add_perm(self, perm):
        "Add permissions to the old ones"
        return permissions.add_perm(self, perm)
    def del_perm(self, perm):
        "Delete permission from old ones"
        return permissions.del_perm(self, perm)

    #
    # PlayerDB class access methods 
    # 
    
    def msg(self, outgoing_string, from_obj=None, data=None):
        """
        Evennia -> User 
        This is the main route for sending data back to the user from the server.
        """
        if from_obj:
            try:
                from_obj.at_msg_send(outgoing_string, self)
            except Exception:
                pass
        if self.character:
            if self.character.at_msg_receive(outgoing_string, from_obj):
                for session in object.__getattribute__(self, 'sessions'):
                    session.msg(outgoing_string, data)

    def swap_character(self, new_character, delete_old_character=False):
        """
        Swaps character, if possible
        """
        return self.__class__.objects.swap_character(self, new_character, delete_old_character=delete_old_character)
    
