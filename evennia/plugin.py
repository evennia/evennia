"""
This provides the base class that all Evennia Plugins must implement to be loadable.

NOTE: Do not add any global imports to this file. It must be totally standalone. The launcher and server both
must be able to import things from it cleanly.
"""


class EvPlugin:
    """
    Base class to use for Evennia Plugins.

    NOTE: the constructor and init_settings methods must not import anything or couple itself to code that's
        server-only. Keep in mind that the Evennia Launcher must also be capable of running __init__ and
        init_settings() !
    """

    def name(self) -> str:
        """
        The name of the plugin. This is how Evennia and other Plugins will refer to it.

        Returns:
            name (str)
        """
        return f"{self.__class__.__module__}.{self.__class__.__name__}"

    def load_priority(self) -> int:
        """
        The order that plugin's load hooks will be called in. the lower the number, the sooner
        it will be called.

        Returns:
            number
        """
        return 0

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


class PluginManager:
    """
    Basic class used for maintaining an index of Plugins installed.
    """

    def __init__(self):
        self.plugins = dict()
        self.plugins_sorted = list()
        self.reverse = None

    def add(self, plugin):
        self.plugins[plugin.name()] = plugin
        self.plugins_sorted.append(plugin)

    def sort(self):
        self.plugins_sorted.sort(key=lambda x: x.load_priority())
        self.reverse = reversed(self.plugins_sorted)

    def __getitem__(self, item):
        return self.plugins[item]

    def init_settings(self, settings):
        for plugin in self.plugins_sorted:
            plugin.init_settings(settings, self.plugins)

    def at_plugin_setup(self):
        for plugin in self.plugins_sorted:
            plugin.at_plugin_setup()

    def at_plugin_collaborate(self):
        for plugin in self.plugins_sorted:
            plugin.at_plugin_collaborate()

    def at_plugin_finalize(self):
        for plugin in self.plugins_sorted:
            plugin.at_plugin_finalize()

    def at_server_start(self):
        for plugin in self.plugins_sorted:
            plugin.at_server_start()

    def at_server_stop(self):
        for plugin in self.reverse:
            plugin.at_server_stop()

    def at_server_reload_start(self):
        for plugin in self.plugins_sorted:
            plugin.at_server_reload_start()

    def at_server_reload_stop(self):
        for plugin in self.reverse:
            plugin.at_server_reload_stop()

    def at_server_cold_start(self):
        for plugin in self.plugins_sorted:
            plugin.at_server_cold_start()

    def at_server_cold_stop(self):
        for plugin in self.reverse:
            plugin.at_server_cold_stop()


def import_property(path):
    """
    Stripped-down version of evennia.utils.utils.class_from_module that gets along with
    django.conf.settings without triggering its setup prematurely.

        Hopefully, a function object or a variable or something of that sort.
    """
    import importlib
    if '.' in path:
        module, thing = path.rsplit('.', 1)
        module = importlib.import_module(module)
        thing = getattr(module, thing)
        return thing
    else:
        return importlib.import_module(path)


_already_configured = False


def plugin_settings(settings_path):
    """
    Run when doing any kind of Django management. Just loads basic plugin settings.
    """
    global _already_configured
    if _already_configured:
        return
    import importlib
    from django.conf import settings
    _settings = importlib.import_module(settings_path)

    _plugins = dict()
    import evennia

    for proto_plugin in set(_settings.PLUGIN_PATHS):
        evennia.PLUGINS.add(import_property(proto_plugin)())
    evennia.PLUGINS.sort()
    evennia.PLUGINS.init_settings(_settings)

    settings.configure(default_settings=_settings)
    _already_configured = True
