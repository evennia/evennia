"""
Styles (playing off CSS) are a way to change the colors and symbols used for standardized
displays used in Evennia. Accounts all have a StyleHandler accessible via .style which
retrieves per-Account settings, falling back to the global settings contained in settings.py.

"""
from django.conf import settings


class StyleHandler(object):
    category = 'style'

    def __init__(self, acc):
        self.acc = acc

    def set(self, option, value):
        pass

    def get(self, option):
        """
        Get the stored Style information from this Account's Attributes if possible.
        If not, fallback to the Global.

        Args:
            option (str): The key of the Style to retrieve.

        Returns:
            String or None
        """
        stored = self.acc.attributes.get(option, category=self.category)
        if stored:
            return stored
        default = settings.DEFAULT_STYLES.get(option, None)
        if default:
            return default[2]
        return None
