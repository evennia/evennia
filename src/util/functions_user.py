"""
User-related functions
"""
from django.contrib.auth.models import User

from src.object.models import Attribute, Object
from src import defines_global

def name_exists(uname):
    """
    Searches for an account first by username, then by alias.

    uname: (string) A username or alias
    
    returns True or False
    """

    # Search for a user object with username = uname
    account = User.objects.filter(username=uname)
    # Look for any objects with an 'Alias' attribute that matches
    # the uname
    alias_matches = Object.objects.filter(attribute__attr_name__exact="ALIAS",
        attribute__attr_value__iexact=uname).filter(
            type=defines_global.OTYPE_PLAYER)
    
    if not account.count() == 0 or not alias_matches.count() == 0:
        return True

    return False

