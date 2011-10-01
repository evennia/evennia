#
# This sets up how models are displayed 
# in the web admin interface. 
#

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group
from src.players.models import PlayerDB, PlayerAttribute

# remove User itself from admin site
admin.site.unregister(User)
#admin.site.unregister(Group)

class PlayerInline(admin.TabularInline):
    model = PlayerDB

class UserAdmin(BaseUserAdmin):
    add_fieldsets = (
        (None, 
         {'fields': ('username', 'email', 'password1', 'password2', ('is_staff', 'is_superuser')),
          'description':'Note that whereas Player name supports spaces, This User field does not!'},),        
        )

admin.site.register(User, UserAdmin)

# class PlayerAttributeAdmin(admin.ModelAdmin):
#     fields = ('db_key', 'db_value')        
# admin.site.register(PlayerAttribute, PlayerAttributeAdmin)

class PlayerAttributeInline(admin.TabularInline):
    model = PlayerAttribute
    #fields = ('db_key', 'db_value')    
    fieldsets = (
        ("Attributes", 
         {'fields'  : (('db_key', 'db_value')),
          'classes' : ('wide',)}), )

    max_num = 1

class PlayerDBAdmin(admin.ModelAdmin):
    inlines = [PlayerAttributeInline]

    list_display = ('id', 'db_key', 'user', 'db_permissions', 'db_typeclass_path')
    list_display_links = ('id', 'db_key')
    ordering = ['db_key', 'db_typeclass_path']
    search_fields = ['^db_key', 'db_typeclass_path']    
    save_as = True 
    save_on_top = True
    list_select_related = True 
    fieldsets = (
        (None, 
         {'fields'     : (('db_key', 'db_typeclass_path'), 'user', ('db_permissions','db_lock_storage'), 'db_obj'),
          'description': 'To create a new Player, a User object must also be created and/or assigned.',
          'classes'    : ('wide', 'extrapretty')}),)

admin.site.register(PlayerDB, PlayerDBAdmin)
