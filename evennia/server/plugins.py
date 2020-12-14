"""
This provides the base class that all Evennia Plugins must implement to be loadable.

NOTE: Do not globally import any Evennia-specific resources into this file.
It must be totally standalone. The launcher and server both
must be able to import things from it cleanly.
"""
from typing import List


class EvPluginVersion:
    """
    Stripped-down, quick 'n dirty Semantic Versioning'y checker.
    """

    def __init__(self, version_string):
        self.major = 0
        self.minor = 0
        self.patch = 0

        if '.' not in version_string:
            # this only has a major version... right?
            self.major = int(version_string)
            return

        # Okay, we have a period. time for enumerate.
        split_ver = version_string.split('.')
        # subversions over the patch will be ignored.
        if len(split_ver) > 3:
            split_ver = split_ver[0:2]

        for i, v in enumerate(version_string.split('.')):
            if i == 0:
                self.major = int(v)
            elif i == 1:
                self.minor = int(v)
            elif i == 2:
                self.patch = int(v)

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self}>"

    def __eq__(self, other):
        return self.major == other.major and self.minor == other.minor and self.patch == other.patch

    def __gt__(self, other):
        if self.major > other.major:
            return True
        else:
            if self.major < other.major:
                return False
            else:
                if self.minor > other.minor:
                    return True
                else:
                    if self.minor < other.minor:
                        return False
                    else:
                        if self.patch > other.patch:
                            return True
                        else:
                            return False

    def __lt__(self, other):
        if self.major < other.major:
            return True
        else:
            if self.major > other.major:
                return False
            else:
                if self.minor < other.minor:
                    return True
                else:
                    if self.minor > other.minor:
                        return False
                    else:
                        if self.patch < other.patch:
                            return True
                        else:
                            return False


class EvPluginRequirement:

    def __init__(self, name: str, ver_eq: str = None, ver_min: str = None, ver_max: str = None):
        self.name = name
        self.ver_eq = EvPluginRequirement(ver_eq) if ver_eq else None
        self.ver_min = EvPluginRequirement(ver_min) if ver_min else None
        self.ver_max = EvPluginRequirement(ver_max) if ver_max else None


class EvPlugin:
    """
    Base class to use for Evennia Plugins.

    NOTE: the constructor and init_settings methods must not import anything or couple itself to code that's
        server-only. Keep in mind that the Evennia Launcher must also be capable of running __init__ and
        init_settings() !
    """

    def __init__(self, manager):
        self.manager = manager

    @property
    def name(self) -> str:
        """
        The name of the plugin. This is how Evennia and other Plugins will refer to it.

        Returns:
            name (str)
        """
        return f"{self.__class__.__module__}.{self.__class__.__name__}"

    @property
    def version(self) -> str:
        """
        A Semantic Versioning style string of this plugin's version. This has nothing to do with Pip,
        but requirements.txt is a good read nonetheless.

        Returns:
            version (str): Such as "1.0.0" or "0.5".
        """
        return "0"

    @property
    def requirements(self) -> List[EvPluginRequirement]:
        """
        Used to tell the Plugin loader what other Plugins this Program requires to function.

        Example of an EvPluginRequirement:
        EvPluginRequirement("plugin_name", ver_min="0.0.5")
        See the constructor of EvPluginRequirement above.

        Returns:
            requirements (list of EvPluginRequirement objects): The requirements of this Plugin.
        """
        return []

    def at_init_settings(self, settings):
        """
        First hook to be called. Override this to make a plugin alter the Evennia settings.py
        during the boot-up process.

        WARNING: This is called by the launcher and possibly in other places, and the run state
            of Evennia is not guaranteed. ONLY use this method to alter the settings.

        Args:
            settings (module): The module reference to settings.py.
        """

    def at_plugin_load_init(self):
        """
        First phase of plugin setup at the end of evennia._init(). The plugin should initialize its basic state that
        does not depend on altering / "arguing with" other plugins.
        """

    def at_plugin_load_patch(self):
        """
        Second phase of plugin setup during evennia._init(). Overload this method for any logic that involves plugins
        directly modifying each other's properties. This is rather dangerous and wild so be careful.
        """

    def at_plugin_load_finalize(self):
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


class PluginManager:
    """
    Basic class used for maintaining an index of Plugins installed.
    """

    def __init__(self):
        print("PLUGIN MANAGER CREATED")
        # each plugin has a name. this dictionary maps that name to the EvPlugin instance.
        self.plugins = {}

        # a dictionary of plugin_name -> EvPluginRequirement versions.
        self.plugin_versions = {}

        # a dictionary of plugin_name -> generated dependencies stored as a cache.
        self.plugin_requirements = {}

        # this is a list which holds plugins in the order they must load to satisfy
        # dependencies. The key is a number that begins at 0 and increments as dependencies climb.
        # IE: Key 0 contains a list of no-dependency plugins that load first. key 1 depends on key 0,
        # key 2 depends on 1 and possibly 0, etc.
        from collections import defaultdict
        self.requirement_tiers = defaultdict(list)

        # Once the dependencies are figured out, the list can be flattened.
        self.plugin_call_order = []

        self.configured = False

    def add(self, plugin: EvPlugin):
        """
        Add a plugin and cache all of its data.

        Args:
            plugin (EvPlugin): The sub-class of plugin to add to the plugin manager.
        """
        name = plugin.name
        self.plugins[name] = plugin
        self.plugin_versions[name] = EvPluginVersion(plugin.version)
        self.plugin_requirements[name] = plugin.requirements

    def __getitem__(self, item):
        return self.plugins[item]

    def dispatch(self, hook: str, *args, **kwargs):
        """
        Dispatches a hook call to all plugins, according to plugin_call_order.

        Args:
            hook (str): The hook to call.
            *args: Any arguments to pass.
            **kwargs: Any kwargs to pass.
        """
        for plugin in self.plugin_call_order:
            c = getattr(plugin, hook, None)
            if c:
                c(*args, **kwargs)

    def satisfied(self, plugin: str) -> bool:
        """
        Check whether a specific plugin's requirements are satisfied.

        Args:
            plugin (str): The name of the plugin being checked.

        Returns:
            true or false
        """
        for req in self.plugin_requirements[plugin]:
            if req.name not in self.plugins:
                return False
            found_ver = self.plugin_versions[req.name]
            if req.ver_eq and (found_ver != req.ver_eq):
                return False
            if req.ver_min and found_ver < req.ver_min:
                return False
            if req.ver_max and found_ver > req.ver_max:
                return False
        return True

    def check_requirements(self):
        """
        Checks dependencies and assembles sorted plugin information for further calls.
        """
        # first, separate plugins based on those with and without dependeices.
        remaining = set()
        loaded = set()

        for k, v in self.plugin_requirements.items():
            if v:
                remaining.add(k)
            else:
                loaded.add(k)
                self.plugin_call_order.append(self.plugins[k])

        for dep in remaining:
            # first we check to make sure that all dependencies are satisfied.
            if not self.satisfied(dep):
                raise Exception("Oops! plugin is not satisfied")

        # now confident that all versions check out, arrange the plugins into a suitable load order.
        # no reason to do anything fancy without requirements though.
        if not remaining:
            return

        while True:
            new_remaining = remaining.copy()
            for p in remaining:
                if loaded.issuperset({r.name for r in self.plugin_requirements[p]}):
                    new_remaining.remove(p)
                    loaded.add(p)
                    self.plugin_call_order.append(self.plugins[p])
            if len(new_remaining) < len(remaining):
                # this is good.. we made progress!
                remaining = new_remaining
                if not remaining:
                    # hooray! No more plugins to process
                    break
            else:
                # this is bad. we are not making progress.
                raise Exception("dependency load order is not progressing!")

    def setup(self, settings_module):
        """
        Import all plugins from their class paths and add their settings to the
        Evennia settings.

        Args:
            settings_module (module): The server.conf.settings module.
        """
        if self.configured:
            return

        for proto_plugin in set(settings_module.PLUGIN_PATHS):
            self.add(import_property(proto_plugin)(self))
        self.check_requirements()

        # At this point, all Plugins know the situation and their dependencies are resolved.
        # They will modify the Django / Evennia settings.
        self.dispatch('at_init_settings', settings_module)

        from django.conf import settings
        settings.configure(default_settings=settings_module)
        self.configured = True


# Creates a global Singleton.
PLUGIN_MANAGER = PluginManager()
