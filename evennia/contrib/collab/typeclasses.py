from evennia.objects.objects import DefaultObject, DefaultRoom, DefaultExit, DefaultCharacter
from evennia.players import DefaultPlayer
from evennia.typeclasses.models import AttributeHandler, DbHolder

# Separate namespaces for different attributes. Each of these classes'
# docstrings explains their intended scope and permissions level. However,
# the appropriate locks can be overwritten in the settings file. See
# collab_settings.py
from evennia.utils import lazy_property


class WizHiddenAttributeHandler(AttributeHandler):
    """
    Attributes which are for wizards to read and write to, but which players
    should not be able to see.

    Examples include
    """
    _attrtype = 'wizh'


class WizAttributeHandler(AttributeHandler):
    """
    Attributes which are accessible to wizards but which the player can
    see.

    Examples include quota overrides, values that are user-settable via
    command but cannot be allowed to be set via the @set command, etc.
    """
    _attrtype = 'wiz'


class ImmortalHiddenAttributeHandler(AttributeHandler):
    """
    Attributes which are more for internal accounting and/or security and
    which should not be exposed to anyone less powerful than an immortal.

    Examples include things like IP information, etc.

    In most cases, the standard 'db' field will work fine for this, since
    collab avoids touching it. However, this type provides a semantic
    distinction, and prevents this data from being exposed should a command
    that isn't collab-aware provide access to information on 'db'.
    """
    _attrtype = 'imh'


class PublicAttributeHandler(AttributeHandler):
    """
    Handles attributes that are public for anyone to set or read.

    These are inherently untrustworthy. They should primarily be used for
    inconsequential storage to spruce up a room without requiring additional
    modules. For example, a description might differ if someone has been to a
    room before. The room could set an attribute on the user to check for this.
    """
    _attrtype = 'pub'


class UserAttributeHandler(AttributeHandler):
    """
    Handles Attributes that are intended for the user to set on themselves.

    These are publicly readable. Examples might include: description, species,
    and sex
    """
    _attrtype = 'usr'


class UserHiddenAttributeHandler(AttributeHandler):
    """
    Handles attributes that the user can set on themselves but which don't need
    to be publicly readable, such as a user's inactive saved descriptions.
    """
    _attrtype = 'usrh'


initializers = [WizHiddenAttributeHandler, WizAttributeHandler,
                ImmortalHiddenAttributeHandler, PublicAttributeHandler,
                UserAttributeHandler, UserHiddenAttributeHandler]


class CollabBase(object):

    def check_protected(self):
        """
        Objects may be marked as 'protected', preventing them from being
        fiddled with by people who normally pass the bypass lock.
        """
        return self.imhdb.protected


for init in initializers:
    key = init._attrtype
    name = init._attrtype + "attributes"
    label = key + 'db'

    # Need to be mindful of closure scoping. Names are looked up at runtime, so
    # we need a function here to freeze the names for these functions.
    # Note that we're doing some variable name shadowing here, taking advantage of
    # variable scoping.
    def make_descriptors(init, key, name, label):
        def getter(self):
            try:
                return getattr(self, '_%s_holder' % key)
            except AttributeError:
                setattr(self, '_%s_holder' % key, DbHolder(self, name))
                return getattr(self, '_%s_holder' % key)

        def setter(self):
            string = "Cannot assign directly to %s object! " % label
            string += "Use %s.attr=value instead." % label
            raise Exception(string)

        def deleter(self):
            "Stop accidental deletion."
            raise Exception("Cannot delete the %s object!" % label)

        def attributes(self):
            return init(self)

        # Needed for the lazy loader.
        attributes.__name__ = name

        return getter, setter, deleter, attributes

    getter, setter, deleter, attributes = make_descriptors(init, key, name, label)

    setattr(CollabBase, label, property(getter, setter, deleter))
    setattr(CollabBase, name, lazy_property(attributes))


class CollabObject(CollabBase, DefaultObject):
    pass


class CollabCharacter(CollabBase, DefaultCharacter):
    pass


class CollabExit(CollabBase, DefaultExit):
    pass


class CollabRoom(CollabBase, DefaultRoom):
    pass


class CollabPlayer(CollabBase, DefaultPlayer):
    pass
