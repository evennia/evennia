from django.contrib import admin
from models import world_rooms, world_exits, world_objects, world_details, personal_objects

# Register your models here.

class WorldRoomsAdmin(admin.ModelAdmin):
    list_display = ('key',
                    'name',
                    'alias',
                    'typeclass',
                    'desc',
                    'location',
                    'home',
                    'lock',
                    'attributes',
                    'tutorial_info',
                    'destination')


class WorldExitsAdmin(admin.ModelAdmin):
    list_display = ('key',
                    'name',
                    'alias',
                    'typeclass',
                    'desc',
                    'location',
                    'home',
                    'lock',
                    'attributes',
                    'tutorial_info',
                    'destination')


class WorldObjectsAdmin(admin.ModelAdmin):
    list_display = ('key',
                    'name',
                    'alias',
                    'typeclass',
                    'desc',
                    'location',
                    'home',
                    'lock',
                    'attributes',
                    'tutorial_info',
                    'destination')


class WorldDetailsAdmin(admin.ModelAdmin):
    list_display = ('key',
                    'name',
                    'desc',
                    'location')


class PersonalObjectsAdmin(admin.ModelAdmin):
    list_display = ('key',
                    'name',
                    'alias',
                    'typeclass',
                    'desc',
                    'location',
                    'home',
                    'lock',
                    'attributes',
                    'tutorial_info',
                    'destination')

admin.site.register(world_rooms, WorldRoomsAdmin)
admin.site.register(world_exits, WorldExitsAdmin)
admin.site.register(world_objects, WorldObjectsAdmin)
admin.site.register(world_details, WorldDetailsAdmin)
admin.site.register(personal_objects, PersonalObjectsAdmin)
