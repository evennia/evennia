#
# This sets up how models are displayed 
# in the web admin interface. 
#

from django import forms
from django.db import models
from django.conf import settings 
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.admin import widgets
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import User
from src.players.models import PlayerDB, PlayerAttribute

# remove User itself from admin site
admin.site.unregister(User)

# handle the custom User editor

class CustomUserChangeForm(UserChangeForm):
    username = forms.RegexField(label="Username", max_length=30, regex=r'^[\w. @+-]+$',widget=forms.TextInput(attrs={'size':'30'}),
                                help_text = "This should be the same as the connected Player's key name. 30 characters or fewer. Letters, spaces, digits and @/./+/-/_ only.",
                                error_messages = {'invalid': "This value may contain only letters, spaces, numbers and @/./+/-/_ characters."}) 
class CustomUserCreationForm(UserCreationForm):
    username = forms.RegexField(label="Username", max_length=30, regex=r'^[\w. @+-]+$',widget=forms.TextInput(attrs={'size':'30'}),
                                help_text = "This should be the same as the connected Player's key name. 30 characters or fewer. Letters, spaces, digits and @/./+/-/_ only.",
                                error_messages = {'invalid': "This value may contain only letters, spaces, numbers and @/./+/-/_ characters."}) 


class UserAdmin(BaseUserAdmin):
    "This will pop up from the Player admin."

    list_display = ('username', 'email', 'is_staff', 'is_superuser')

    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    add_fieldsets = (
        (None, 
         {'fields': ('username', 'email', 'password1', 'password2', ('is_staff', 'is_superuser')),
          'description':"The <i>User</i> object holds all authentication information and bits for using the admin site. A <i>superuser</i> account represents  a 'God user' in-game. This User account should have the same username as its corresponding <i>Player</i> object has; the two are always uniquely connected to each other."},),)
admin.site.register(User, UserAdmin)


# The Player editor 
class PlayerAttributeForm(forms.ModelForm):
    "Defines how to display the atttributes"
    class Meta:
        model = PlayerAttribute
    db_key = forms.CharField(label="Key", widget=forms.TextInput(attrs={'size':'15'}))
    db_value = forms.CharField(label="Value", widget=forms.Textarea(attrs={'rows':'2'}))

class PlayerAttributeInline(admin.TabularInline):
    "Inline creation of player attributes"    
    model = PlayerAttribute
    extra = 1
    form = PlayerAttributeForm
    fieldsets = (
        (None, {'fields'  : (('db_key', 'db_value'))}),)

class PlayerEditForm(forms.ModelForm):
    "This form details the look of the fields"

    class Meta:
        # important! This allows us to not excplicitly add all fields.
        model = PlayerDB

    db_key = forms.RegexField(label="Username", max_length=30, regex=r'^[\w. @+-]+$', widget=forms.TextInput(attrs={'size':'30'}),
         help_text = "this should be the same as the User's name. 30 characters or fewer. Letters, spaces, digits and @/./+/-/_ only.")
    db_typeclass_path = forms.CharField(label="Typeclass",initial=settings.BASE_PLAYER_TYPECLASS, widget=forms.TextInput(attrs={'size':'78'}),
         help_text="this defines what 'type' of entity this is. This variable holds a Python path to a module with a valid Evennia Typeclass.")
    db_permissions = forms.CharField(label="Permissions", initial=settings.PERMISSION_PLAYER_DEFAULT,required=False,
         help_text="a comma-separated list of text strings checked by certain locks. They are often used for hierarchies, such as letting a Player have permission 'Wizards', 'Builders' etc. A Player permission can be overloaded by the permissions of a controlled Character. Normal players use 'Players' by default.")
    db_lock_storage = forms.CharField(label="Locks", widget=forms.Textarea(attrs={'cols':'100', 'rows':'1'}),
                                      required=False,
         help_text="locks limit access to an entity. A lock is defined as a 'lock string' on the form 'type:lockfunctions', defining what functionality is locked and how to determine access. This is set to a default upon creation.")
    db_cmdset_storage = forms.CharField(label="cmdset", initial=settings.CMDSET_OOC, widget=forms.TextInput(attrs={'size':'78'}),
                                        required=False,
                                        help_text="python path to cmdset class.")
class PlayerCreateForm(forms.ModelForm):
    "This form details the look of the fields"

    class Meta:
        # important! This allows us to not excplicitly add all fields.
        model = PlayerDB

    db_key = forms.RegexField(label="Username", max_length=30, regex=r'^[\w. @+-]+$', widget=forms.TextInput(attrs={'size':'30'}),
         help_text = "this should be the same as the User's name. 30 characters or fewer. Letters, spaces, digits and @/./+/-/_ only.")
    db_typeclass_path = forms.CharField(label="Typeclass",initial=settings.BASE_PLAYER_TYPECLASS, widget=forms.TextInput(attrs={'size':'78'}),
         help_text="this defines what 'type' of entity this is. This variable holds a Python path to a module with a valid Evennia Typeclass.")
    db_permissions = forms.CharField(label="Permissions", initial=settings.PERMISSION_PLAYER_DEFAULT,required=False,
         help_text="a comma-separated list of text strings checked by certain locks. They are often used for hierarchies, such as letting a Player have permission 'Wizards', 'Builders' etc. A Player permission can be overloaded by the permissions of a controlled Character. Normal players use 'Players' by default.")
    db_cmdset_storage = forms.CharField(label="cmdset", initial=settings.CMDSET_OOC, widget=forms.TextInput(attrs={'size':'78'}),
                                        required=False,
                                        help_text="python path to cmdset class.")
        
class PlayerDBAdmin(admin.ModelAdmin):
    "Setting up and tying the player administration together"

    list_display = ('id', 'db_key', 'user', 'db_obj', 'db_permissions', 'db_typeclass_path')
    list_display_links = ('id', 'db_key')
    ordering = ['db_key', 'db_typeclass_path']
    search_fields = ['^db_key', 'db_typeclass_path']    
    save_as = True 
    save_on_top = True
    list_select_related = True 

    # editing/adding player 
    form = PlayerEditForm
    fieldsets = (
        (None,          
          {'fields'     : (('db_key', 'db_typeclass_path'), 'user', ('db_permissions','db_lock_storage'), 'db_cmdset_storage', 'db_obj'),
          'description': 'To create a new Player, a User object must also be created and/or assigned. When deleting a Player, its connected User will also be deleted. A Character object is optional, but required for IC interactions in the game.',
          'classes'    : ('wide', 'extrapretty')}),)

    # deactivated, they cause empty players to be created in admin.
    #inlines = [PlayerAttributeInline]

    add_form = PlayerCreateForm
    add_fieldsets = (
        (None,          
          {'fields'     : (('db_key', 'db_typeclass_path'), 'user', 'db_permissions', 'db_cmdset_storage', 'db_obj'),
          'description': 'To create a new Player, a User object must also be created and/or assigned. When deleting a Player, its connected User will also be deleted. A Character object is optional, but required for IC interactions in the game.',
          'classes'    : ('wide', 'extrapretty')}),)

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super(PlayerDBAdmin, self).get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during creation
        """
        defaults = {}
        if obj is None:
            defaults.update({
                    'form': self.add_form,
                    'fields': admin.util.flatten_fieldsets(self.add_fieldsets),
                    })
            defaults.update(kwargs)
        return super(PlayerDBAdmin, self).get_form(request, obj, **defaults)

    def save_model(self, request, obj, form, change):
        if not change:
            # adding a new object
            new_obj = obj.typeclass
            new_obj.basetype_setup()            
            new_obj.at_player_creation()            
            if new_obj.obj:
                char = new_obj.db_obj
                char.db_player = obj
                char.save() 
            new_obj.at_init()
        else:
            if obj.db_obj:
                char = obj.db_obj
                char.db_player = obj
                char.save()            

            obj.at_init()

    def delete_model(self, request, obj):
        # called when deleting a player object. Makes sure to also delete user. 
        user = obj.user 
        user.delete()

admin.site.register(PlayerDB, PlayerDBAdmin)
