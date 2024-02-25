import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from evennia.accounts.models import AccountDB


class EvenniaUsernameAvailabilityValidator:
    """
    Checks to make sure a given username is not taken or otherwise reserved.
    """

    def __call__(self, username):
        """
        Validates a username to make sure it is not in use or reserved.

        Args:
            username (str): Username to validate

        Returns:
            None (None): None if password successfully validated,
                raises ValidationError otherwise.

        """
        # Check guest list
        if settings.GUEST_LIST and username.lower() in (
            guest.lower() for guest in settings.GUEST_LIST
        ):
            raise ValidationError(
                _("Sorry, that username is reserved."), code="evennia_username_reserved"
            )

        # Check database
        exists = AccountDB.objects.filter(username__iexact=username).exists()
        if exists:
            raise ValidationError(
                _("Sorry, that username is already taken."), code="evennia_username_taken"
            )
