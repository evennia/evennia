"""
The managers for the custom Player object and permissions.
"""

import datetime
from django.utils import timezone
from django.contrib.auth.models import UserManager
#from functools import update_wrapper
from evennia.typeclasses.managers import (returns_typeclass_list, returns_typeclass,
                                      TypedObjectManager, TypeclassManager)
#from evennia.utils import logger
__all__ = ("PlayerManager",)


#
# Player Manager
#

class PlayerDBManager(TypedObjectManager, UserManager):
    """
    This PlayerManager implements methods for searching
    and manipulating Players directly from the database.

    Evennia-specific search methods (will return Characters if
    possible or a Typeclass/list of Typeclassed objects, whereas
    Django-general methods will return Querysets or database objects):

    dbref (converter)
    dbref_search
    get_dbref_range
    object_totals
    typeclass_search
    num_total_players
    get_connected_players
    get_recently_created_players
    get_recently_connected_players
    get_player_from_email
    get_player_from_uid
    get_player_from_name
    player_search (equivalent to evennia.search_player)
    #swap_character

    """
    def num_total_players(self):
        """
        Returns the total number of registered players.
        """
        return self.count()

    @returns_typeclass_list
    def get_connected_players(self):
        """
        Returns a list of player objects with currently connected users/players.
        """
        return self.filter(db_is_connected=True)

    @returns_typeclass_list
    def get_recently_created_players(self, days=7):
        """
        Returns a QuerySet containing the player User accounts that have been
        connected within the last <days> days.
        """
        end_date = timezone.now()
        tdelta = datetime.timedelta(days)
        start_date = end_date - tdelta
        return self.filter(date_joined__range=(start_date, end_date))

    @returns_typeclass_list
    def get_recently_connected_players(self, days=7):
        """
        Returns a QuerySet containing the player accounts that have been
        connected within the last <days> days.

        days - number of days backwards to check
        """
        end_date = timezone.now()
        tdelta = datetime.timedelta(days)
        start_date = end_date - tdelta
        return self.filter(last_login__range=(
                start_date, end_date)).order_by('-last_login')

    @returns_typeclass
    def get_player_from_email(self, uemail):
        """
        Returns a player object when given an email address.
        """
        return self.filter(email__iexact=uemail)

    @returns_typeclass
    def get_player_from_uid(self, uid):
        """
        Returns a player object based on User id.
        """
        try:
            return self.get(id=uid)
        except self.model.DoesNotExist:
            return None

    @returns_typeclass
    def get_player_from_name(self, uname):
        "Get player object based on name"
        try:
            return self.get(username__iexact=uname)
        except self.model.DoesNotExist:
            return None

    @returns_typeclass_list
    def player_search(self, ostring, exact=True):
        """
        Searches for a particular player by name or
        database id.

        ostring - a string or database id.
        exact - allow for a partial match
        """
        dbref = self.dbref(ostring)
        if dbref or dbref == 0:
            # bref search is always exact
            matches = self.filter(id=dbref)
            if matches:
                return matches
        if exact:
            return self.filter(username__iexact=ostring)
        else:
            return self.filter(username__icontains=ostring)

#    def swap_character(self, player, new_character, delete_old_character=False):
#        """
#        This disconnects a player from the current character (if any) and
#        connects to a new character object.
#
#        """
#
#        if new_character.player:
#            # the new character is already linked to a player!
#            return False
#
#        # do the swap
#        old_character = player.character
#        if old_character:
#            old_character.player = None
#        try:
#            player.character = new_character
#            new_character.player = player
#        except Exception:
#            # recover old setup
#            if old_character:
#                old_character.player = player
#                player.character = old_character
#            return False
#        if old_character and delete_old_character:
#            old_character.delete()
#        return True

class PlayerManager(PlayerDBManager, TypeclassManager):
    pass
