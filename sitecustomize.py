"""
This special Python config file sets the default encoding for
the codebase to UTF-8 instead of ascii. This allows for just
about any language to be used in-game.

It is not advisable to change the value set below, as
there will be a lot of encoding errors that result in
server crashes.
"""
import sys
sys.setdefaultencoding('utf-8')
