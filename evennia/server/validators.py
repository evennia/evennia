from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
import re

class EvenniaPasswordValidator:
    
    def __init__(self, regex=r"^[\w. @+\-',]+$", policy="Password should contain a mix of letters, spaces, digits and @/./+/-/_/'/, only."):
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
            raise ValidationError(
                _(self.policy),
                code='evennia_password_policy',
            )

    def get_help_text(self):
        """
        Returns a user-facing explanation of the password policy defined
        by this validator.
    
        Returns:
            text (str): Explanation of password policy.
    
        """
        return _(
            "%s From a terminal client, you can also use a phrase of multiple words if you enclose the password in double quotes." % self.policy
        )