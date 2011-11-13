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
from src.utils import logger, create
        
# remove User itself from admin site
admin.site.unregister(User)

# handle the custom User editor
class CustomUserChangeForm(UserChangeForm):
    username = forms.RegexField(label="Username", 
                                max_length=30, 
                                regex=r'^[\w. @+-]+$',
                                widget=forms.TextInput(attrs={'size':'30'}),
                                error_messages = {'invalid': "This value may contain only letters, spaces, numbers and @/./+/-/_ characters."}, 
                                help_text = "30 characters or fewer. Letters, spaces, digits and @/./+/-/_ only.")

class CustomUserCreationForm(UserCreationForm):
    username = forms.RegexField(label="Username", 
                                max_length=30, 
                                regex=r'^[\w. @+-]+$',
                                widget=forms.TextInput(attrs={'size':'30'}),
                                error_messages = {'invalid': "This value may contain only letters, spaces, numbers and @/./+/-/_ characters."}, 
                                help_text = "30 characters or fewer. Letters, spaces, digits and @/./+/-/_ only.")

# # The Player editor 
# class PlayerAttributeForm(forms.ModelForm):
#     "Defines how to display the atttributes"
#     class Meta:
#         model = PlayerAttribute
#     db_key = forms.CharField(label="Key", 
#                              widget=forms.TextInput(attrs={'size':'15'}))
#     db_value = forms.CharField(label="Value", 
#                                widget=forms.Textarea(attrs={'rows':'2'}))

# class PlayerAttributeInline(admin.TabularInline):
#     "Inline creation of player attributes"    
#     model = PlayerAttribute
#     extra = 0
#     form = PlayerAttributeForm
#     fieldsets = (
#         (None, {'fields'  : (('db_key', 'db_value'))}),)

class PlayerForm(forms.ModelForm):
    "Defines how to display Players"

    class Meta:
        model = PlayerDB
    db_key = forms.RegexField(label="Username", 
                              initial="PlayerDummy",
                              max_length=30, 
                              regex=r'^[\w. @+-]+$',
                              required=False, 
                              widget=forms.TextInput(attrs={'size':'30'}),
                              error_messages = {'invalid': "This value may contain only letters, spaces, numbers and @/./+/-/_ characters."}, 
                              help_text = "This should be the same as the connected Player's key name. 30 characters or fewer. Letters, spaces, digits and @/./+/-/_ only.")

    db_typeclass_path = forms.CharField(label="Typeclass",
                                        initial=settings.BASE_PLAYER_TYPECLASS, 
                                        widget=forms.TextInput(attrs={'size':'78'}),
                                        help_text="Required. Defines what 'type' of entity this is. This variable holds a Python path to a module with a valid Evennia Typeclass. Defaults to settings.BASE_PLAYER_TYPECLASS.")
    db_permissions = forms.CharField(label="Permissions", 
                                     initial=settings.PERMISSION_PLAYER_DEFAULT,
                                     required=False,
                                     widget=forms.TextInput(attrs={'size':'78'}),
                                     help_text="In-game permissions. A comma-separated list of text strings checked by certain locks. They are often used for hierarchies, such as letting a Player have permission 'Wizards', 'Builders' etc. A Player permission can be overloaded by the permissions of a controlled Character. Normal players use 'Players' by default.")
    db_lock_storage = forms.CharField(label="Locks", 
                                      widget=forms.Textarea(attrs={'cols':'100', 'rows':'2'}),
                                      required=False,
                                      help_text="In-game lock definition string. If not given, defaults will be used. This string should be on the form <i>type:lockfunction(args);type2:lockfunction2(args);...")
    db_cmdset_storage = forms.CharField(label="cmdset", 
                                        initial=settings.CMDSET_OOC, 
                                        widget=forms.TextInput(attrs={'size':'78'}),
                                        required=False,
                                        help_text="python path to player cmdset class (settings.CMDSET_OOC by default)")
       
class PlayerInline(admin.StackedInline):
    "Inline creation of Player"
    model = PlayerDB
    template = "admin/players/stacked.html"
    form = PlayerForm
    fieldsets = (
        ("In-game Permissions and Locks",
         {'fields': ('db_permissions', 'db_lock_storage'),
          'description':"<i>These are permissions/locks for in-game use. They are unrelated to website access rights.</i>"}),
        ("In-game Player data",
         {'fields':('db_typeclass_path', 'db_cmdset_storage'),
          'description':"<i>These fields define in-game-specific properties for the Player object in-game.</i>"}),
        ("Evennia In-game Character",
         {'fields':('db_obj',),
          'description': "<i>To actually play the game, a Player must control a Character. This could be added in-game instead of from here if some sort of character creation system is in play. If not, you should normally create a new Character here rather than assigning an existing one. Observe that the admin does not check for puppet-access rights when assigning Characters! If not creating a new Character, make sure the one you assign is not puppeted by someone else!</i>"}))
    

    extra = 1
    max_num = 1
    
class UserAdmin(BaseUserAdmin):
    "This is the main creation screen for Users/players"

    list_display = ('username','email', 'is_staff', 'is_superuser')
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    inlines = [PlayerInline]
    add_form_template = "admin/players/add_form.html"
    change_form_template = "admin/players/change_form.html"
    change_list_template = "admin/players/change_list.html"
    fieldsets = (
        (None, {'fields': ('username', 'password', 'email')}),
        ('Website profile', {'fields': ('first_name', 'last_name'),
                           'description':"<i>These are not used in the default system.</i>"}),
        ('Website dates', {'fields': ('last_login', 'date_joined'),
                             'description':'<i>Relevant only to the website.</i>'}),
        ('Website Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions','groups'),
                                 'description': "<i>These are permissions/permission groups for accessing the admin site. They are unrelated to in-game access rights.</i>"}),)


    add_fieldsets = (
        (None, 
         {'fields': ('username', 'password1', 'password2', 'email'),
          'description':"<i>These account details are shared by the admin system and the game.</i>"},),)

    def save_formset(self, request, form, formset, change):        
        "Run all hooks on the player object"
        super(UserAdmin, self).save_formset(request, form, formset, change)
        playerdb = form.instance.get_profile()
        if not change:            
            create.create_player("", "", "", 
                                 typeclass=playerdb.db_typeclass_path,
                                 create_character=False,
                                 player_dbobj=playerdb)
        if playerdb.db_obj:
            playerdb.db_obj.db_player = playerdb
            playerdb.db_obj.save()
        
        #assert False, (form.instance, form.instance.get_profile())
        
admin.site.register(User, UserAdmin)
