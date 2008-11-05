from apps.config.models import ConfigValue

def general_context(request):
    """
    Returns common Evennia-related context stuff.
    """
    return {
        'game_name': ConfigValue.objects.get_configvalue('site_name'),
    }
