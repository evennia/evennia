from django.utils.translation import ugettext as _

_STRING = {
    "AUTH_SUCCESS": _("Authentication Success"),
    "AUTH_FAILURE": _("Authentication Failure"),
    "PUPPET_SUCCESS": _("You are now puppeting "),
    "PUPPET_FAILURE": _("You cannot puppet this object."),
    "PUPPET_FAILURE_DUPE": _("You are already puppeting this object."),
    "PUPPET_FAILURE_AUTH": _("You don't have permission to puppet"),
    "PUPPET_FAILURE_SECOND": _("is already puppeted by another account."),
    "PUPPET_FAILURE_DOESNOTEXIST": _("This Character does not exist."),
    "PUPPET_MULTISESSION_SHARED": _("is now shared from another of your sessions."),
    "PUPPET_MULTISESSION_TAKER": _("is being taken from another of your sessions."),
    "PUPPET_MULTISESSION_TAKEE": _("is now acted from another of your sessions."),
    "GUEST_NOT_ENABLED": _("Guest accounts are not enabledo n this server."),
    "GUEST_FULL": _("All guest accounts are in use. Please try again later."),
    "ERR_IMPORT": _(
        "This module could not be imported. Check your AUTH_USERNAME_VALIDATORS setting."
    ),
    "ERR_BANNED_THROTTLE": _("Too many sightings of banned artifact."),
    "ERR_CREATION_THROTTLE": _(
        "You are creating too many accounts. Please log into an existing account."
    ),
    "LOGIN_FAILURE_INVALID_USERPASS": _("Username and/or password is incorrect."),
    "LOGIN_FAILURE_THROTTLE": _(
        "Too many authentication failures; please try again in a few minutes."
    ),
    "LOGIN_FAILURE_BANNED": _(
        "You have been banned and cannot continue from here.\nIf you feel this ban is in error, please contact an admin."
    ),
    "PASSWORD_CHANGE_SUCCESS": _("Password successfully changed"),
    "ACCOUNT_CREATION_SUCCESS": _("Account Created"),
    "ACCOUNT_CREATION_FAILURE": _(
        "There was an error creating the Account. If this problem persists, contact an admin."
    ),
    "CHANNEL_NOCONNECT": _("Could not connect to channel"),
    "ERR_UNSPECIFIED": _(
        "An unspecified error has occurred. Please contact an admin if this problem persists."
    ),
    "ACCOUNT_DELETED": _("Account has been deleted."),
    "SELFREFERENCE_REGEX": _(
        "*me|*self"
    ),  # TODO: IMPLEMENT i18N for Self-Referencing variables
    "CONNECT_SUCCESS": _("is connected."),
    "DISCONNECT_SUCCESS": _("has disconnected."),
    "NOT_IN_GAME": _("is not in the game"),
    "CHARACTER_OOC": _("You are 'Out of Character' (OOC)"),
    "CHARACTERS_NONE": _(
        "You don't have any characters yet. See |whelp @charcreate|n for creating one."
    ),
    "CHARACTERS_PLAYED_BY_YOU": _("Played by you in session"),
    "CHARACTERS_PLAYED_BY_OTHER": _("Played by someone else"),
}
