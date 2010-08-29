"""
Configuration model - storing global flags on the fly, as
                      opposed to what is set once and for all 
                      in the settings file. 

ConnectScreen model - cycling connect screens
"""

from django.db import models
from src.utils.idmapper.models import SharedMemoryModel
from src.config.manager import ConfigValueManager
from src.config.manager import ConnectScreenManager

#------------------------------------------------------------
#
# ConfigValue
#
#------------------------------------------------------------
            
class ConfigValue(SharedMemoryModel):
    """
    On-the fly storage of global settings. 

    Properties defined on ConfigValue:
      key - main identifier
      value - value stored in key

    """

    #
    # ConfigValue database model setup
    #
    #
    # These database fields are all set using their corresponding properties,
    # named same as the field, but withtout the db_* prefix.

    # main name of the database entry
    db_key = models.CharField(max_length=100)
    # config value
    db_value = models.TextField()

    # Database manager
    objects = ConfigValueManager()
        
    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value, 
    # value = self.attr and del self.attr respectively (where self 
    # is the object in question).
        
    # key property (wraps db_key)
    #@property
    def key_get(self):
        "Getter. Allows for value = self.key"
        return self.db_key
    #@key.setter
    def key_set(self, value):
        "Setter. Allows for self.key = value"
        self.db_key = value
        self.save()
    #@key.deleter
    def key_del(self):
        "Deleter. Allows for del self.key. Deletes entry."
        self.delete()
    key = property(key_get, key_set, key_del)

    # value property (wraps db_value)
    #@property
    def value_get(self):
        "Getter. Allows for value = self.value"
        return self.db_value
    #@value.setter
    def value_set(self, value):
        "Setter. Allows for self.value = value"
        self.db_value = value
        self.save()
    #@value.deleter
    def value_del(self):
        "Deleter. Allows for del self.value. Deletes entry."
        self.delete()
    value = property(value_get, value_set, value_del)

    class Meta:
        "Define Django meta options"
        verbose_name = "Server Config value"
        verbose_name_plural = "Server Config values"

    # 
    # ConfigValue other methods 
    #

    def __unicode__(self):
        return "%s" % self.key

#------------------------------------------------------------
## ConnectScreen
#
#------------------------------------------------------------
            
class ConnectScreen(SharedMemoryModel):
    """
    Stores connect screens. The admins may have only one or multiple, which
    will cycle randomly.

    Properties on ConnectScreen:
      key - optional identifier
      text - the text to show
      is_active - if the screen is in rotation

    """
    
    #
    # ConnectScreen database model setup
    #
    # These database fields are all set using their corresponding properties,
    # named same as the field, but withtout the db_* prefix.
    #
    
    # optional identifier
    db_key = models.CharField(max_length=255, blank=True)
    # connect screen text (ansi may be used)
    db_text = models.TextField()
    # if this screen should be used in rotation
    db_is_active = models.BooleanField(default=True)
    
    # Database manager
    objects = ConnectScreenManager()
    
    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value, 
    # value = self.attr and del self.attr respectively (where self 
    # is the object in question).
    
    # key property (wraps db_key)
    #@property
    def key_get(self):
        "Getter. Allows for value = self.key"
        return self.db_key
    #@key.setter
    def key_set(self, value):
        "Setter. Allows for self.key = value"
        self.db_key = value
        self.save()
    #@key.deleter
    def key_del(self):
        "Deleter. Allows for del self.key. Deletes entry."
        self.delete()
    key = property(key_get, key_set, key_del)

    # text property (wraps db_text)
    #@property
    def text_get(self):
        "Getter. Allows for value = self.text"
        return self.db_text
    #@text.setter
    def text_set(self, value):
        "Setter. Allows for self.text = value"
        self.db_text = value
        self.save()
    #@text.deleter
    def text_del(self):
        "Deleter. Allows for del self.text."
        raise Exception("You can't delete the text of the connect screen!")
    text = property(text_get, text_set, text_del)

    # is_active property (wraps db_is_active)
    #@property
    def is_active_get(self):
        "Getter. Allows for value = self.is_active"
        return self.db_is_active
    #@is_active.setter
    def is_active_set(self, value):
        "Setter. Allows for self.is_active = value"
        self.db_is_active = value
        self.save()
    #@is_active.deleter
    def is_active_del(self):
        "Deleter. Allows for del self.is_active."
        self.db_is_active = False
        self.save()
    is_active = property(is_active_get, is_active_set, is_active_del)

    class Meta:
        "Define Django meta options"
        verbose_name = "Connect Screen"
        verbose_name_plural = "Connect Screens"
