from django.contrib.auth.models import User, Group
from src.objects.models import Object
from src.config.models import ConfigValue
from src import comsys, defines_global

def handle_setup():
    # Set the initial user's username on the #1 object.
    god_user = User.objects.get(id=1)
    god_user_obj = Object(id=1, type=defines_global.OTYPE_PLAYER)
    god_user_obj.set_name(god_user.username)
    god_user_obj.save()
    
    limbo_obj = Object()
    limbo_obj.type = defines_global.OTYPE_ROOM
    limbo_obj.owner = god_user_obj
    limbo_obj.set_name('Limbo')
    limbo_obj.save()
    
    god_user_obj.home = limbo_obj
    god_user_obj.save()

    groups = ("Immortals", "Wizards", "Builders", "Player Helpers")
    for group in groups:
        newgroup = Group()
        newgroup.name = group
        newgroup.save()

    chan_pub = comsys.create_channel("Public", god_user_obj, description="Public Discussion")
    chan_pub.is_joined_by_default = True
    chan_pub.save()
    comsys.create_channel("Errors", god_user_obj, description="Error log")
    comsys.create_channel("Info", god_user_obj, description="Informative messages")

    # We don't want to do initial setup tasks every startup, only the first.
    ConfigValue.objects.set_configvalue('game_firstrun', '0')
