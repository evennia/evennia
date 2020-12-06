"""
This provides the base class that all Evennia Plugins must implement to be loadable.

NOTE: Do not add any global imports to this file. It must be totally standalone.
"""


class EvPlugin:

    @property
    def name(self) -> str:
        """
        The name of the plugin. This is how Evennia and other Plugins will refer to it.

        Returns:
            name (str)
        """
        return f"{self.__class__.__module__}.{self.__class__.__name__}"

    @property
    def load_priority(self) -> int:
        """
        The order that plugin's load hooks will be called in. the lower the number, the sooner
        it will be called.

        Returns:
            number
        """

    def init_settings(self, settings, plugins):
        """
        First hook to be called. Override this to make a plugin alter the Evennia settings.py
        during the boot-up process.

        WARNING: This is called by the launcher and possibly in other places, and the run state
            of Evennia is not guaranteed. ONLY use this method to alter the settings.

        Args:
            settings (settings.py): The module reference to settings.py.
            plugins (dict of name->EvPlugin classes): Allows plugins to know what
                plugins will be loading.

        Returns:
            None
        """

    def at_plugin_setup(self):
        """
        First phase of plugin setup at the end of evennia._init()
        """

    def at_plugin_collaborate(self):
        """
        Second phase of plugin setup during evennia._init(). At this point, all plugins
        are available in the evennia.PLUGINS dictionary.

        Use this method for any plugin setup that involves plugins collaborating with each other.
        """

    def at_plugin_finalize(self):
        """
        Third and final phase of plugin setup during evennia._init(). Any last steps? Do them here.
        """

    def at_server_start(self):
        """
        Runs in the same order as load_priority, but before the 'mygame' hooks.

        see at_server_startstop module documentation.
        """

    def at_server_stop(self):
        """
        Runs in the reverse order of load_priority, but before the 'mygame' hooks.

        see at_server_startstop module documentation.
        """

    def at_server_reload_start(self):
        """
       Runs in the same order as load_priority, but before the 'mygame' hooks.

       see at_server_startstop module documentation.
       """

    def at_server_reload_stop(self):
        """
        Runs in the reverse order of load_priority, but before the 'mygame' hooks.

        see at_server_startstop module documentation.
        """

    def at_server_cold_start(self):
        """
       Runs in the same order as load_priority, but before the 'mygame' hooks.

       see at_server_startstop module documentation.
       """

    def at_server_cold_stop(self):
        """
        Runs in the reverse order of load_priority, but before the 'mygame' hooks.

        see at_server_startstop module documentation.
        """
