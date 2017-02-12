"""
This module contains historical deprecations that the Evennia launcher
checks for.

These all print to the terminal.
"""

def check_errors(settings):
    """
    Check for deprecations that are critical errors and should stop
    the launcher.

    Args:
        settings (Settings): The Django settings file
    Raises:
        DeprecationWarning

    """
    from django.conf import settings
    def imp(path, split=True):
        mod, fromlist = path, "None"
        if split:
            mod, fromlist = path.rsplit('.', 1)
        __import__(mod, fromlist=[fromlist])

    # core modules
    imp(settings.COMMAND_PARSER)
    imp(settings.SEARCH_AT_RESULT)
    imp(settings.CONNECTION_SCREEN_MODULE)
    #imp(settings.AT_INITIAL_SETUP_HOOK_MODULE, split=False)
    for path in settings.LOCK_FUNC_MODULES:
        imp(path, split=False)
    # cmdsets

    deprstring = ("settings.%s should be renamed to %s. If defaults are used, "
                  "their path/classname must be updated "
                  "(see evennia/settings_default.py).")
    if hasattr(settings, "CMDSET_DEFAULT"):
        raise DeprecationWarning(deprstring % (
            "CMDSET_DEFAULT", "CMDSET_CHARACTER"))
    if hasattr(settings, "CMDSET_OOC"):
        raise DeprecationWarning(deprstring % ("CMDSET_OOC", "CMDSET_PLAYER"))
    if settings.WEBSERVER_ENABLED and not isinstance(settings.WEBSERVER_PORTS[0], tuple):
        raise DeprecationWarning(
            "settings.WEBSERVER_PORTS must be on the form "
            "[(proxyport, serverport), ...]")
    if hasattr(settings, "BASE_COMM_TYPECLASS"):
        raise DeprecationWarning(deprstring % (
            "BASE_COMM_TYPECLASS", "BASE_CHANNEL_TYPECLASS"))
    if hasattr(settings, "COMM_TYPECLASS_PATHS"):
        raise DeprecationWarning(deprstring % (
            "COMM_TYPECLASS_PATHS", "CHANNEL_TYPECLASS_PATHS"))
    if hasattr(settings, "CHARACTER_DEFAULT_HOME"):
        raise DeprecationWarning(
            "settings.CHARACTER_DEFAULT_HOME should be renamed to "
            "DEFAULT_HOME. See also settings.START_LOCATION "
            "(see evennia/settings_default.py).")
    deprstring = ("settings.%s is now merged into settings.TYPECLASS_PATHS. "
                  "Update your settings file.")
    if hasattr(settings, "OBJECT_TYPECLASS_PATHS"):
        raise DeprecationWarning(deprstring % "OBJECT_TYPECLASS_PATHS")
    if hasattr(settings, "SCRIPT_TYPECLASS_PATHS"):
        raise DeprecationWarning(deprstring % "SCRIPT_TYPECLASS_PATHS")
    if hasattr(settings, "PLAYER_TYPECLASS_PATHS"):
        raise DeprecationWarning(deprstring % "PLAYER_TYPECLASS_PATHS")
    if hasattr(settings, "CHANNEL_TYPECLASS_PATHS"):
        raise DeprecationWarning(deprstring % "CHANNEL_TYPECLASS_PATHS")
    if hasattr(settings, "SEARCH_MULTIMATCH_SEPARATOR"):
        raise DeprecationWarning(
        "settings.SEARCH_MULTIMATCH_SEPARATOR was replaced by "
        "SEARCH_MULTIMATCH_REGEX and SEARCH_MULTIMATCH_TEMPLATE. "
        "Update your settings file (see evennia/settings_default.py "
        "for more info).")

    from evennia.commands import cmdsethandler
    if not cmdsethandler.import_cmdset(settings.CMDSET_UNLOGGEDIN, None):
        print("Warning: CMDSET_UNLOGGED failed to load!")
    if not cmdsethandler.import_cmdset(settings.CMDSET_CHARACTER, None):
        print("Warning: CMDSET_CHARACTER failed to load")
    if not cmdsethandler.import_cmdset(settings.CMDSET_PLAYER, None):
        print("Warning: CMDSET_PLAYER failed to load")
    # typeclasses
    imp(settings.BASE_PLAYER_TYPECLASS)
    imp(settings.BASE_OBJECT_TYPECLASS)
    imp(settings.BASE_CHARACTER_TYPECLASS)
    imp(settings.BASE_ROOM_TYPECLASS)
    imp(settings.BASE_EXIT_TYPECLASS)
    imp(settings.BASE_SCRIPT_TYPECLASS)

def check_warnings(settings):
    """
    Check deprecations that should produce warnings but which
    does not stop launch.
    """
