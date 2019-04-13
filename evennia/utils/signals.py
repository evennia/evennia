from django.dispatch import Signal


ACCOUNT_CREATE = Signal(providing_args=['session', ])

ACCOUNT_RENAME = Signal(providing_args=['old_name', 'new_name'])

ACCOUNT_LOGIN = Signal(providing_args=['session', ])

ACCOUNT_LOGOUT = Signal()

OBJECT_PUPPET = Signal(providing_args=['session', 'account'])

OBJECT_UNPUPPET = Signal(providing_args=['session', 'account'])

