#
# This sets up how models are displayed 
# in the web admin interface. 
#

from src.players.models import PlayerDB, PlayerAttribute
from django.contrib import admin

class PlayerAttributeAdmin(admin.ModelAdmin):
    list_display = ('id', 'db_key', 'db_value', 'db_mode', 'db_obj')
    list_display_links = ("id", 'db_key')
    ordering = ["db_obj", 'db_key']
    search_fields = ['id', 'db_key', 'db_obj']
    save_as = True 
    save_on_top = True   
    list_select_related = True 
admin.site.register(PlayerAttribute, PlayerAttributeAdmin)

class PlayerDBAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'db_obj', 'db_typeclass_path')
    list_display_links = ('id', 'user')
    ordering = ['id', 'user']
    search_fields = ['^db_key', 'db_typeclass_path']
    save_as = True 
    save_on_top = True
    list_select_related = True 
admin.site.register(PlayerDB, PlayerDBAdmin)
