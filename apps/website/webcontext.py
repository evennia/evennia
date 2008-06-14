import gameconf

def general_context(request):
    """
    Returns common Evennia-related context stuff.
    """
    return {
        'game_name': gameconf.get_configvalue('site_name'),
    }
