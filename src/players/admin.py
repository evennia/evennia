#
# This sets up how models are displayed 
# in the web admin interface. 
#

from django.contrib import admin
from django.contrib.auth.models import User, Group
from src.players.models import PlayerDB, PlayerAttribute

# remove User itself from admin site
admin.site.unregister(User)
admin.site.unregister(Group)

class PlayerAttributeInline(admin.StackedInline):
    model = PlayerAttribute
    fields = ('db_key', 'db_value')

class PlayerDBAdmin(admin.ModelAdmin):
    inlines = [PlayerAttributeInline]

    # list_display = ('id', 'user', 'db_obj', 'db_typeclass_path')
    # list_display_links = ('id', 'user')
    # ordering = ['id', 'user']
    search_fields = ['^db_key', 'db_typeclass_path']
    save_as = True 
    save_on_top = True
    list_select_related = True 
        
admin.site.register(PlayerDB, PlayerDBAdmin)
