"""
Django application configuration for the Aetos Web Client contrib.

Registering Aetos as a Django application is what allows it to ship its own
templates and static assets from inside the contrib directory, using Django's
standard app-directory loaders. No files are copied into the game directory and
no Evennia core file is modified.

"""

from django.apps import AppConfig


class AetosWebClientConfig(AppConfig):
    """Application config for the Aetos Web Client."""

    name = "evennia.contrib.base_systems.aetos_webclient"
    label = "aetos_webclient"
    verbose_name = "Aetos Web Client"

    def ready(self):
        """
        Register Aetos's startup checks.

        Imported here rather than at module level because the checks read
        settings and import the validators, and neither is safe before Django
        has finished loading applications.

        """
        from evennia.contrib.base_systems.aetos_webclient import checks  # noqa: F401
