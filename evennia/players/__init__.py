"""
This sub-package defines the out-of-character entities known as
Players.  These are equivalent to 'accounts' and can puppet one or
more Objects depending on settings. A Player has no in-game existence.

"""
from __future__ import absolute_import
from .players import DefaultGuest, DefaultPlayer
