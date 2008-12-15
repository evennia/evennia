from django.contrib.auth.models import User, Group
from src.objects.models import Object
from src.config.models import ConfigValue

def handle_setup():
    # Set the initial user's username on the #1 object.
    god_user = User.objects.filter(id=1)[0]
    god_user_obj = Object.objects.filter(id=1)[0]
    god_user_obj.set_name(god_user.username)

    groups = ("Immortals", "Wizards", "Builders", "Player Helpers")
    for group in groups:
        newgroup = Group()
        newgroup.name = group
        newgroup.save()

    # We don't want to do initial setup tasks every startup, only the first.
    ConfigValue.objects.set_configvalue('game_firstrun', '0')
