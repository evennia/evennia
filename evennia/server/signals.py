"""
This module brings Django Signals into Evennia. These are events that can be
subscribed to by importing a given Signal and using the following code.

```python
THIS_SIGNAL.connect(callback, sender_object)
```

When other code calls `THIS_SIGNAL.send(sender, **kwargs)`, the callback will
be triggered.

Callbacks must be on the following format:

```python
def my_callback(sender, **kwargs):
    # ...
```

This is used on top of hooks to make certain features easier to add to contribs
without necessitating a full takeover of hooks that may be in high demand.

"""
from django.dispatch import Signal

# The sender is the created Account. This is triggered at the very end of
# Account.create() after the Account is created. Note that this will *not* fire
# if calling create.create_account alone, since going through the Account.create()
# is the most expected route.
# sends with kwarg 'ip'
SIGNAL_ACCOUNT_POST_CREATE = Signal()

# The Sender is the renamed Account. This is triggered by the username setter in AccountDB.
# sends with kwargs 'old_name' and 'new_name'
SIGNAL_ACCOUNT_POST_RENAME = Signal()

# The Sender is the connecting Account. This is triggered when an Account connects cold;
# that is, it had no other sessions connected.
# sends with kwarg 'session'
SIGNAL_ACCOUNT_POST_FIRST_LOGIN = Signal()

# The sender is the connecting Account. This is triggered whenever a session authenticates
# to an Account regardless of existing sessions. It then firest after FIRST_LOGIN signal
# sends with kwarg 'session'
SIGNAL_ACCOUNT_POST_LOGIN = Signal()

# The Sender is the Account attempting to authenticate. This is triggered whenever a
# session tries to login to an Account but fails.
# sends with kwarg 'session'
SIGNAL_ACCOUNT_POST_LOGIN_FAIL = Signal()

# The sender is the disconnecting Account. This is triggered whenever a session disconnects
# from the account, regardless of how many it started with or remain.
# sends with kwarg 'session'
SIGNAL_ACCOUNT_POST_LOGOUT = Signal()

# The sender is the Account. This is triggered when an Account's final session disconnects.
# sends with kwarg 'session'
SIGNAL_ACCOUNT_POST_LAST_LOGOUT = Signal()

# The sender is an Object. This is triggered when Object has been created, after all hooks.
SIGNAL_OBJECT_POST_CREATE = Signal()

# The sender is the Object being puppeted. This is triggered after all puppeting hooks have
# been called. The Object has already been puppeted by this point.
# sends with kwargs 'session', 'account'
SIGNAL_OBJECT_POST_PUPPET = Signal()

# The sender is the Object being released. This is triggered after all hooks are called.
# The Object is no longer puppeted by this point.
# sends with kwargs 'session', 'account'
SIGNAL_OBJECT_POST_UNPUPPET = Signal()

# The sender is the Typed Object being renamed. This isn't necessarily an Object;
# it could be a script. It fires whenever the value of the Typed object's 'key'
# changes. Will need to use isinstance() or other filtering on things that use this.
# sends with kwargs 'old_key', 'new_key'
SIGNAL_TYPED_OBJECT_POST_RENAME = Signal()

# The sender is the created Script. This is called after the Script was first created,
# after all hooks.
SIGNAL_SCRIPT_POST_CREATE = Signal()

# The sender is a newly created help entry. This called after the entry was first created.
SIGNAL_HELPENTRY_POST_CREATE = Signal()

# The sender is a newly created Channel. This is called after the Channel was
# first created, after all hooks.
SIGNAL_CHANNEL_POST_CREATE = Signal()

# The sender is the exit used when traversing, as well as 'traverser', for the one traversing
# Called just after at_traverse hook.
SIGNAL_EXIT_TRAVERSED = Signal()

# Django default signals (https://docs.djangoproject.com/en/2.2/topics/signals/)

from django.core.signals import request_finished  # "             ends.
from django.core.signals import request_started  # Sent when HTTP request begins.
from django.db.backends.signals import (  # Sent when making initial connection to database
    connection_created,
)
from django.db.models.signals import m2m_changed  # Sent when a ManyToManyField changes.
from django.db.models.signals import post_delete  # after         "
from django.db.models.signals import post_init  # end
from django.db.models.signals import post_migrate  # after     "
from django.db.models.signals import post_save  # after            "
from django.db.models.signals import pre_delete  # Sent before an object is deleted.
from django.db.models.signals import pre_migrate  # Sent before migration starts
from django.db.models.signals import (
    pre_save,  # Sent before a typeclass' .save is called.
)
from django.db.models.signals import (  # Sent at start of typeclass __init__ (before at_init)
    pre_init,
)
from django.test.signals import (
    setting_changed,  # Sent when setting changes from override
)
from django.test.signals import (
    template_rendered,  # Sent when test system renders template
)
