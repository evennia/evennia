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


class EvenniaPasswordValidator:
    def __init__(
        self,
        regex=r"^[\w. @+\-',]+$",
        policy="Password should contain a mix of letters, "
        "spaces, digits and @/./+/-/_/'/, only.",
    ):
        """
        Constructs a standard Django password validator.

        Args:
            regex (str): Regex pattern of valid characters to allow.
            policy (str): Brief explanation of what the defined regex permits.

        """
        self.regex = regex
        self.policy = policy

    def validate(self, password, user=None):
        """
        Validates a password string to make sure it meets predefined Evennia
        acceptable character policy.

        Args:
            password (str): Password to validate
            user (None): Unused argument but required by Django

        Returns:
            None (None): None if password successfully validated,
                raises ValidationError otherwise.

        """
        # Check complexity
        if not re.findall(self.regex, password):
            raise ValidationError(_(self.policy), code="evennia_password_policy")

    def get_help_text(self):
        """
        Returns a user-facing explanation of the password policy defined
        by this validator.

        Returns:
            text (str): Explanation of password policy.

        """
        return _(
            "{policy} From a terminal client, you can also use a phrase of multiple words if "
            "you enclose the password in double quotes.".format(policy=self.policy)
        )
