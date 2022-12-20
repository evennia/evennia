"""
This module contains historical deprecations that the Evennia launcher
checks for.

These all print to the terminal.
"""
import os


def check_errors(settings):
    """
    Check for deprecations that are critical errors and should stop
    the launcher.

    Args:
        settings (Settings): The Django settings file

    Raises:
        DeprecationWarning if a critical deprecation is found.

    """
    deprstring = (
        "settings.%s should be renamed to %s. If defaults are used, "
        "their path/classname must be updated "
        "(see evennia/settings_default.py)."
    )
    if hasattr(settings, "CMDSET_DEFAULT"):
        raise DeprecationWarning(deprstring % ("CMDSET_DEFAULT", "CMDSET_CHARACTER"))
    if hasattr(settings, "CMDSET_OOC"):
        raise DeprecationWarning(deprstring % ("CMDSET_OOC", "CMDSET_ACCOUNT"))
    if settings.WEBSERVER_ENABLED and not isinstance(settings.WEBSERVER_PORTS[0], tuple):
        raise DeprecationWarning(
            "settings.WEBSERVER_PORTS must be on the form [(proxyport, serverport), ...]"
        )
    if hasattr(settings, "BASE_COMM_TYPECLASS"):
        raise DeprecationWarning(deprstring % ("BASE_COMM_TYPECLASS", "BASE_CHANNEL_TYPECLASS"))
    if hasattr(settings, "COMM_TYPECLASS_PATHS"):
        raise DeprecationWarning(deprstring % ("COMM_TYPECLASS_PATHS", "CHANNEL_TYPECLASS_PATHS"))
    if hasattr(settings, "CHARACTER_DEFAULT_HOME"):
        raise DeprecationWarning(
            "settings.CHARACTER_DEFAULT_HOME should be renamed to "
            "DEFAULT_HOME. See also settings.START_LOCATION "
            "(see evennia/settings_default.py)."
        )
    deprstring = (
        "settings.%s is now merged into settings.TYPECLASS_PATHS. Update your settings file."
    )
    if hasattr(settings, "OBJECT_TYPECLASS_PATHS"):
        raise DeprecationWarning(deprstring % "OBJECT_TYPECLASS_PATHS")
    if hasattr(settings, "SCRIPT_TYPECLASS_PATHS"):
        raise DeprecationWarning(deprstring % "SCRIPT_TYPECLASS_PATHS")
    if hasattr(settings, "ACCOUNT_TYPECLASS_PATHS"):
        raise DeprecationWarning(deprstring % "ACCOUNT_TYPECLASS_PATHS")
    if hasattr(settings, "CHANNEL_TYPECLASS_PATHS"):
        raise DeprecationWarning(deprstring % "CHANNEL_TYPECLASS_PATHS")
    if hasattr(settings, "SEARCH_MULTIMATCH_SEPARATOR"):
        raise DeprecationWarning(
            "settings.SEARCH_MULTIMATCH_SEPARATOR was replaced by "
            "SEARCH_MULTIMATCH_REGEX and SEARCH_MULTIMATCH_TEMPLATE. "
            "Update your settings file (see evennia/settings_default.py "
            "for more info)."
        )
    depstring = (
        "settings.{} was renamed to {}. Update your settings file (the FuncParser "
        "replaces and generalizes that which inlinefuncs used to do)."
    )
    if hasattr(settings, "INLINEFUNC_ENABLED"):
        raise DeprecationWarning(
            depstring.format(
                "settings.INLINEFUNC_ENABLED", "FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED"
            )
        )
    if hasattr(settings, "INLINEFUNC_STACK_MAXSIZE"):
        raise DeprecationWarning(
            depstring.format("settings.INLINEFUNC_STACK_MAXSIZE", "FUNCPARSER_MAX_NESTING")
        )
    if hasattr(settings, "INLINEFUNC_MODULES"):
        raise DeprecationWarning(
            depstring.format("settings.INLINEFUNC_MODULES", "FUNCPARSER_OUTGOING_MESSAGES_MODULES")
        )
    if hasattr(settings, "PROTFUNC_MODULES"):
        raise DeprecationWarning(
            depstring.format("settings.PROTFUNC_MODULES", "FUNCPARSER_PROTOTYPE_VALUE_MODULES")
        )

    gametime_deprecation = (
        "The settings TIME_SEC_PER_MIN, TIME_MIN_PER_HOUR,"
        "TIME_HOUR_PER_DAY, TIME_DAY_PER_WEEK, \n"
        "TIME_WEEK_PER_MONTH and TIME_MONTH_PER_YEAR "
        "are no longer supported. Remove them from your "
        "settings file to continue.\nIf you want to use "
        "and manipulate these time units, the tools from utils.gametime "
        "are now found in contrib/convert_gametime.py instead."
    )
    if any(
        hasattr(settings, value)
        for value in (
            "TIME_SEC_PER_MIN",
            "TIME_MIN_PER_HOUR",
            "TIME_HOUR_PER_DAY",
            "TIME_DAY_PER_WEEK",
            "TIME_WEEK_PER_MONTH",
            "TIME_MONTH_PER_YEAR",
        )
    ):
        raise DeprecationWarning(gametime_deprecation)

    game_directory_deprecation = (
        "The setting GAME_DIRECTORY_LISTING was removed. It must be "
        "renamed to GAME_INDEX_LISTING instead."
    )
    if hasattr(settings, "GAME_DIRECTORY_LISTING"):
        raise DeprecationWarning(game_directory_deprecation)

    chan_connectinfo = settings.CHANNEL_CONNECTINFO
    if chan_connectinfo is not None and not isinstance(chan_connectinfo, dict):
        raise DeprecationWarning(
            "settings.CHANNEL_CONNECTINFO has changed. It "
            "must now be either None or a dict "
            "specifying the properties of the channel to create."
        )
    if hasattr(settings, "CYCLE_LOGFILES"):
        raise DeprecationWarning(
            "settings.CYCLE_LOGFILES is unused and should be removed. "
            "Use PORTAL/SERVER_LOG_DAY_ROTATION and PORTAL/SERVER_LOG_MAX_SIZE "
            "to control log cycling."
        )
    if hasattr(settings, "CHANNEL_COMMAND_CLASS") or hasattr(settings, "CHANNEL_HANDLER_CLASS"):
        raise DeprecationWarning(
            "settings.CHANNEL_HANDLER_CLASS and CHANNEL COMMAND_CLASS are "
            "unused and should be removed. The ChannelHandler is no more; "
            "channels are now handled by aliasing the default 'channel' command."
        )

    template_overrides_dir = os.path.join(settings.GAME_DIR, "web", "template_overrides")
    static_overrides_dir = os.path.join(settings.GAME_DIR, "web", "static_overrides")
    if os.path.exists(template_overrides_dir):
        raise DeprecationWarning(
            f"The template_overrides directory ({template_overrides_dir}) has changed name.\n"
            " - Rename your existing `template_overrides` folder to `templates` instead."
        )
    if os.path.exists(static_overrides_dir):
        raise DeprecationWarning(
            f"The static_overrides directory ({static_overrides_dir}) has changed name.\n"
            " 1. Delete any existing `web/static` folder and all its contents (this "
            "was auto-generated)\n"
            " 2. Rename your existing `static_overrides` folder to `static` instead."
        )

    if settings.MULTISESSION_MODE < 2 and settings.MAX_NR_SIMULTANEOUS_PUPPETS > 1:
        raise DeprecationWarning(
            f"settings.MULTISESSION_MODE={settings.MULTISESSION_MODE} is not compatible with "
            f"settings.MAX_NR_SIMULTANEOUS_PUPPETS={settings.MAX_NR_SIMULTANEOUS_PUPPETS}. "
            "To allow multiple simultaneous puppets, the multi-session mode must be higher than 1."
        )


def check_warnings(settings):
    """
    Check conditions and deprecations that should produce warnings but which
    does not stop launch.
    """
    if settings.DEBUG:
        print(" [Devel: settings.DEBUG is True. Important to turn off in production.]")
    if settings.IN_GAME_ERRORS:
        print(" [Devel: settings.IN_GAME_ERRORS is True. Turn off in production.]")
    if settings.ALLOWED_HOSTS == ["*"]:
        print(" [Devel: settings.ALLOWED_HOSTS set to '*' (all). Limit in production.]")
    if settings.SERVER_HOSTNAME == "localhost":
        print(
            " [Devel: settings.SERVER_HOSTNAME is set to 'localhost'. "
            "Update to the actual hostname in production.]"
        )

    for dbentry in settings.DATABASES.values():
        if "psycopg" in dbentry.get("ENGINE", ""):
            print(
                'Deprecation: postgresql_psycopg2 backend is deprecated". '
                "Switch settings.DATABASES to use "
                '"ENGINE": "django.db.backends.postgresql instead"'
            )
