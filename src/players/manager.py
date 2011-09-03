"""
The managers for the custom Player object and permissions.
"""

import datetime 
from django.db import models
from django.contrib.auth.models import User
from src.typeclasses.managers import returns_typeclass_list, returns_typeclass, TypedObjectManager
from src.utils import logger

#
# Player Manager
#

def returns_player_list(method):
    """
    decorator that makes sure that a method
    returns a Player object instead of a User
    one (if you really want the User object, not
    the player, use the player's 'user' property)
    """
    def func(self, *args, **kwargs):
        "This *always* returns a list."
        match = method(self, *args, **kwargs)
        if not match:
            return []
        try:
            match = list(match)
        except TypeError:
            match = [match]
        players = []
        for user in match:
            try:
                players.append(user.get_profile())
            except Exception:
                # there is something wrong with get_profile. But
                # there is a 1-1 relation between Users-Players, so we 
                # try to go the other way instead.
                from src.players.models import PlayerDB
                match = PlayerDB.objects.filter(user=user)
                if match:
                    players.append(match[0])
                else:
                    logger.log_trace("No connection User<->Player, maybe database was partially reset?")                
        return players
    return func 

def returns_player(method):
    """
    Decorator: Always returns a single result or None.
    """
    def func(self, *args, **kwargs):
        "decorator"
        rfunc = returns_player_list(method)
        match = rfunc(self, *args, **kwargs)
        if match:
            return match[0]
        else:
            return None 
    return func

class PlayerManager(TypedObjectManager):
    """
    Custom manager for the player profile model. We use this
    to wrap users in general in evennia, and supply some useful
    search/statistics methods. 

    Note how ALL these commands return character objects if possible. 
    """
    def num_total_players(self):
        """
        Returns the total number of registered users/players.
        """
        return self.count()
    
    @returns_typeclass_list
    def get_connected_players(self):
        """
        Returns a list of player objects with currently connected users/players.
        """
        return [player for player in self.all() if player.sessions]

    @returns_typeclass_list
    @returns_player_list 
    def get_recently_created_players(self, days=7):
        """
        Returns a QuerySet containing the player User accounts that have been
        connected within the last <days> days.
        """
        end_date = datetime.datetime.now()
        tdelta = datetime.timedelta(days)
        start_date = end_date - tdelta
        return User.objects.filter(date_joined__range=(start_date, end_date))

    @returns_typeclass_list
    @returns_player_list
    def get_recently_connected_players(self, days=7):
        """
        Returns a QuerySet containing the player User accounts that have been
        connected within the last <days> days.
        """
        end_date = datetime.datetime.now()
        tdelta = datetime.timedelta(days)
        start_date = end_date - tdelta
        return User.objects.filter(last_login__range=(
                start_date, end_date)).order_by('-last_login')

    @returns_typeclass
    @returns_player
    def get_player_from_email(self, uemail):
        """
        Returns a player object when given an email address.
        """
        return User.objects.filter(email__iexact=uemail)

    @returns_typeclass
    @returns_player
    def get_player_from_uid(self, uid):
        """
        Returns a player object based on User id.
        """
        return User.objects.get(id=uid)

    @returns_typeclass
    def get_player_from_name(self, uname):
        "Get player object based on name"
        players = self.filter(user__username=uname)
        if players:
            return players[0]
        return None 
    
    # @returns_typeclass_list
    # def get_players_with_perm(self, permstring):
    #     """
    #     Returns all players having access according to the given
    #     permission string.
    #     """
    #     return [player for player in self.all()
    #             if player.has_perm(permstring)]

    # @returns_typeclass_list
    # def get_players_with_group(self, groupstring):
    #     """
    #     Returns all players belonging to the given group. 
    #     """
    #     return [player.user for player in self.all()
    #             if player.has_group(groupstring)]

    @returns_typeclass_list
    def player_search(self, ostring):
        """
        Searches for a particular player by name or 
        database id.
        
        ostring = a string or database id.
        """
        ostring = ostring.lstrip("*")
        dbref = self.dbref(ostring)
        if dbref:
            matches = self.filter(id=dbref)
            if matches:
                return matches
        return self.filter(user__username__iexact=ostring)            

    def swap_character(self, player, new_character, delete_old_character=False):
        """
        This disconnects a player from the current character (if any) and connects
        to a new character object.

        """

        if new_character.player:
            # the new character is already linked to a player!
            return False

        # do the swap
        old_character = player.character            
        if old_character:
            old_character.player = None
        try:
            player.character = new_character
            new_character.player = player
        except Exception:
            # recover old setup
            old_character.player = player
            player.character = old_character
            return False 
        if delete_old_character:
            old_character.delete()
        return True 
        
