"""
The managers for the custom Account object and permissions.
"""

import datetime
from django.utils import timezone
from django.contrib.auth.models import UserManager
from evennia.typeclasses.managers import TypedObjectManager, TypeclassManager

__all__ = ("AccountManager",)


#
# Account Manager
#


class AccountDBManager(TypedObjectManager, UserManager):
    """
    This AccountManager implements methods for searching
    and manipulating Accounts directly from the database.

    Evennia-specific search methods (will return Characters if
    possible or a Typeclass/list of Typeclassed objects, whereas
    Django-general methods will return Querysets or database objects):

    dbref (converter)
    dbref_search
    get_dbref_range
    object_totals
    typeclass_search
    num_total_accounts
    get_connected_accounts
    get_recently_created_accounts
    get_recently_connected_accounts
    get_account_from_email
    get_account_from_uid
    get_account_from_name
    account_search (equivalent to evennia.search_account)

    """

    def num_total_accounts(self):
        """
        Get total number of accounts.

        Returns:
            count (int): The total number of registered accounts.

        """
        return self.count()

    def get_connected_accounts(self):
        """
        Get all currently connected accounts.

        Returns:
            count (list): Account objects with currently
                connected sessions.

        """
        return self.filter(db_is_connected=True)

    def get_recently_created_accounts(self, days=7):
        """
        Get accounts recently created.

        Args:
            days (int, optional): How many days in the past "recently" means.

        Returns:
            accounts (list): The Accounts created the last `days` interval.

        """
        end_date = timezone.now()
        tdelta = datetime.timedelta(days)
        start_date = end_date - tdelta
        return self.filter(date_joined__range=(start_date, end_date))

    def get_recently_connected_accounts(self, days=7):
        """
        Get accounts recently connected to the game.

        Args:
            days (int, optional): Number of days backwards to check

        Returns:
            accounts (list): The Accounts connected to the game in the
                last `days` interval.

        """
        end_date = timezone.now()
        tdelta = datetime.timedelta(days)
        start_date = end_date - tdelta
        return self.filter(last_login__range=(start_date, end_date)).order_by("-last_login")

    def get_account_from_email(self, uemail):
        """
        Search account by
        Returns an account object based on email address.

        Args:
            uemail (str): An email address to search for.

        Returns:
            account (Account): A found account, if found.

        """
        return self.filter(email__iexact=uemail)

    def get_account_from_uid(self, uid):
        """
        Get an account by id.

        Args:
            uid (int): Account database id.

        Returns:
            account (Account): The result.

        """
        try:
            return self.get(id=uid)
        except self.model.DoesNotExist:
            return None

    def get_account_from_name(self, uname):
        """
        Get account object based on name.

        Args:
            uname (str): The Account name to search for.

        Returns:
            account (Account): The found account.

        """
        try:
            return self.get(username__iexact=uname)
        except self.model.DoesNotExist:
            return None

    def search_account(self, ostring, exact=True, typeclass=None):
        """
        Searches for a particular account by name or
        database id.

        Args:
            ostring (str or int): A key string or database id.
            exact (bool, optional): Only valid for string matches. If
                `True`, requires exact (non-case-sensitive) match,
                otherwise also match also keys containing the `ostring`
                (non-case-sensitive fuzzy match).
            typeclass (str or Typeclass, optional): Limit the search only to
                accounts of this typeclass.

        """
        dbref = self.dbref(ostring)
        if dbref or dbref == 0:
            # bref search is always exact
            matches = self.filter(id=dbref)
            if matches:
                return matches
        query = {"username__iexact" if exact else "username__icontains": ostring}
        if typeclass:
            # we accept both strings and actual typeclasses
            if callable(typeclass):
                typeclass = f"{typeclass.__module__}.{typeclass.__name__}"
            else:
                typeclass = str(typeclass)
            query["db_typeclass_path"] = typeclass
        if exact:
            matches = self.filter(**query)
        else:
            matches = self.filter(**query)
        if not matches:
            # try alias match
            matches = self.filter(
                db_tags__db_tagtype__iexact="alias",
                **{"db_tags__db_key__iexact" if exact else "db_tags__db_key__icontains": ostring},
            )
        return matches

    # back-compatibility alias
    account_search = search_account


class AccountManager(AccountDBManager, TypeclassManager):
    pass
