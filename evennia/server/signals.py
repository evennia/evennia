"""
This module brings Django Signals into Evennia. These are events that
can be subscribed to by importing a given Signal and using the
following code.

THIS_SIGNAL.connect(callback, sender_object)

When other code calls THIS_SIGNAL.send(sender, **kwargs), the callback
will be triggered.

Callbacks must be in the following format:

def my_callback(sender, **kwargs):
    ...

This is used on top of hooks to make certain features easier to
add to contribs without necessitating a full takeover of hooks
that may be in high demand.

"""
from django.dispatch import Signal

# The sender is the created Account. This is triggered at the very end of
# Account.create() after the Account is created. Note that this will *not* fire
# if calling create.create_account alone, since going through the Account.create()
# is the most expected route.
SIGNAL_ACCOUNT_POST_CREATE = Signal(providing_args=["ip"])

# The Sender is the renamed Account. This is triggered by the username setter in AccountDB.
SIGNAL_ACCOUNT_POST_RENAME = Signal(providing_args=["old_name", "new_name"])

# The Sender is the connecting Account. This is triggered when an Account connects cold;
# that is, it had no other sessions connected.
SIGNAL_ACCOUNT_POST_FIRST_LOGIN = Signal(providing_args=["session"])

# The sender is the connecting Account. This is triggered whenever a session authenticates
# to an Account regardless of existing sessions. It then firest after FIRST_LOGIN signal
SIGNAL_ACCOUNT_POST_LOGIN = Signal(providing_args=["session"])

# The Sender is the Account attempting to authenticate. This is triggered whenever a
# session tries to login to an Account but fails.
SIGNAL_ACCOUNT_POST_LOGIN_FAIL = Signal(providing_args=["session"])

# The sender is the disconnecting Account. This is triggered whenever a session disconnects
# from the account, regardless of how many it started with or remain.
SIGNAL_ACCOUNT_POST_LOGOUT = Signal(providing_args=["session"])

# The sender is the Account. This is triggered when an Account's final session disconnects.
SIGNAL_ACCOUNT_POST_LAST_LOGOUT = Signal(providing_args=["session"])

# The sender is an Object. This is triggered when Object has been created, after all hooks.
SIGNAL_OBJECT_POST_CREATE = Signal()

# The sender is the Object being puppeted. This is triggered after all puppeting hooks have
# been called. The Object has already been puppeted by this point.
SIGNAL_OBJECT_POST_PUPPET = Signal(providing_args=["session", "account"])

# The sender is the Object being released. This is triggered after all hooks are called.
# The Object is no longer puppeted by this point.
SIGNAL_OBJECT_POST_UNPUPPET = Signal(providing_args=["session", "account"])

# The sender is the Typed Object being renamed. This isn't necessarily an Object;
# it could be a script. It fires whenever the value of the Typed object's 'key'
# changes. Will need to use isinstance() or other filtering on things that use this.
SIGNAL_TYPED_OBJECT_POST_RENAME = Signal(providing_args=["old_key", "new_key"])

# The sender is the created Script. This is called after the Script was first created,
# after all hooks.
SIGNAL_SCRIPT_POST_CREATE = Signal()

# The sender is a newly created help entry. This called after the entry was first created.
SIGNAL_HELPENTRY_POST_CREATE = Signal()

# The sender is a newly created Channel. This is called after the Channel was
# first created, after all hooks.
SIGNAL_CHANNEL_POST_CREATE = Signal()

# Django default signals (https://docs.djangoproject.com/en/2.2/topics/signals/)

from django.db.models.signals import (
    pre_save,  # Sent before a typeclass' .save is called.
    post_save,  #       after            "
    pre_delete,  # Sent before an object is deleted.
    post_delete,  #       after         "
    m2m_changed,  # Sent when a ManyToManyField changes.
    pre_migrate,  # Sent before migration starts
    post_migrate,  #     after     "
    pre_init,  # Sent at start of typeclass __init__ (before at_init)
    post_init,  #        end
)
from django.core.signals import (
    request_started,  # Sent when HTTP request begins.
    request_finished,  #         "             ends.
)
from django.test.signals import (
    setting_changed,  # Sent when setting changes from override
    template_rendered,  # Sent when test system renders template
)
from django.db.backends.signals import (
    connection_created,  # Sent when making initial connection to database
)
