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
        Get total number of players.

        Returns:
            count (int): The total number of registered players.

        """
        return self.count()

    @returns_typeclass_list
    def get_connected_players(self):
        """
        Get all currently connected players.

        Returns:
            count (list): Player objects with currently
                connected sessions.

        """
        return self.filter(db_is_connected=True)

    @returns_typeclass_list
    def get_recently_created_players(self, days=7):
        """
        Get players recently created.

        Args:
            days (int, optional): How many days in the past "recently" means.

        Returns:
            players (list): The Players created the last `days` interval.

        """
        end_date = timezone.now()
        tdelta = datetime.timedelta(days)
        start_date = end_date - tdelta
        return self.filter(date_joined__range=(start_date, end_date))

    @returns_typeclass_list
    def get_recently_connected_players(self, days=7):
        """
        Get players recently connected to the game.

        Args:
            days (int, optional): Number of days backwards to check

        Returns:
            players (list): The Players connected to the game in the
                last `days` interval.

        """
        end_date = timezone.now()
        tdelta = datetime.timedelta(days)
        start_date = end_date - tdelta
        return self.filter(last_login__range=(
                start_date, end_date)).order_by('-last_login')

    @returns_typeclass
    def get_player_from_email(self, uemail):
        """
        Search player by
        Returns a player object based on email address.

        Args:
            uemail (str): An email address to search for.

        Returns:
            player (Player): A found player, if found.

        """
        return self.filter(email__iexact=uemail)

    @returns_typeclass
    def get_player_from_uid(self, uid):
        """
        Get a player by id.

        Args:
            uid (int): Player database id.

        Returns:
            player (Player): The result.

        """
        try:
            return self.get(id=uid)
        except self.model.DoesNotExist:
            return None

    @returns_typeclass
    def get_player_from_name(self, uname):
        """
        Get player object based on name.

        Args:
            uname (str): The Player name to search for.

        Returns:
            player (Player): The found player.

        """
        try:
            return self.get(username__iexact=uname)
        except self.model.DoesNotExist:
            return None

    @returns_typeclass_list
    def player_search(self, ostring, exact=True):
        """
        Searches for a particular player by name or
        database id.

        Args:
            ostring (str or int): A key string or database id.
            exact (bool, optional): Only valid for string matches. If
                `True`, requires exact (non-case-sensitive) match,
                otherwise also match also keys containing the `ostring`
                (non-case-sensitive fuzzy match).

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


class PlayerManager(PlayerDBManager, TypeclassManager):
    pass
