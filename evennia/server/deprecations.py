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
            "settings.WEBSERVER_PORTS must be on the form " "[(proxyport, serverport), ...]"
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
        "settings.%s is now merged into settings.TYPECLASS_PATHS. " "Update your settings file."
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
