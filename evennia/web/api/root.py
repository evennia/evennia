"""
Set a more useful description on the Api root.

"""

from rest_framework import routers


class EvenniaAPIRoot(routers.APIRootView):
    """
    Root of the Evennia API tree.

    """

    pass


class APIRootRouter(routers.DefaultRouter):
    APIRootView = EvenniaAPIRoot
