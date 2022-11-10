"""
The managers for the custom Account object and permissions.
"""

import datetime

from django.conf import settings
from django.contrib.auth.models import UserManager
from django.utils import timezone

from evennia.server import signals
from evennia.typeclasses.managers import TypeclassManager, TypedObjectManager
from evennia.utils.utils import class_from_module, dbid_to_obj, make_iter

__all__ = ("AccountManager", "AccountDBManager")


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
        Returns:
            Queryset: A queryset (an iterable) with 0, 1 or more matches.

        """
        dbref = self.dbref(ostring)
        if dbref or dbref == 0:
            # dbref search is always exact
            dbref_match = self.search_dbref(dbref)
            if dbref_match:
                return dbref_match

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

    def create_account(
        self,
        key,
        email,
        password,
        typeclass=None,
        is_superuser=False,
        locks=None,
        permissions=None,
        tags=None,
        attributes=None,
        report_to=None,
    ):
        """
        This creates a new account.

        Args:
            key (str): The account's name. This should be unique.
            email (str or None): Email on valid addr@addr.domain form. If
                the empty string, will be set to None.
            password (str): Password in cleartext.

        Keyword Args:
            typeclass (str): The typeclass to use for the account.
            is_superuser (bool): Whether or not this account is to be a superuser
            locks (str): Lockstring.
            permission (list): List of permission strings.
            tags (list): List of Tags on form `(key, category[, data])`
            attributes (list): List of Attributes on form
                 `(key, value [, category, [,lockstring [, default_pass]]])`
            report_to (Object): An object with a msg() method to report
                errors to. If not given, errors will be logged.

        Returns:
            Account: The newly created Account.
        Raises:
            ValueError: If `key` already exists in database.


        Notes:
            Usually only the server admin should need to be superuser, all
            other access levels can be handled with more fine-grained
            permissions or groups. A superuser bypasses all lock checking
            operations and is thus not suitable for play-testing the game.

        """
        typeclass = typeclass if typeclass else settings.BASE_ACCOUNT_TYPECLASS
        locks = make_iter(locks) if locks is not None else None
        permissions = make_iter(permissions) if permissions is not None else None
        tags = make_iter(tags) if tags is not None else None
        attributes = make_iter(attributes) if attributes is not None else None

        if isinstance(typeclass, str):
            # a path is given. Load the actual typeclass.
            typeclass = class_from_module(typeclass, settings.TYPECLASS_PATHS)

        # setup input for the create command. We use AccountDB as baseclass
        # here to give us maximum freedom (the typeclasses will load
        # correctly when each object is recovered).

        if not email:
            email = None
        if self.model.objects.filter(username__iexact=key):
            raise ValueError("An Account with the name '%s' already exists." % key)

        # this handles a given dbref-relocate to an account.
        report_to = dbid_to_obj(report_to, self.model)

        # create the correct account entity, using the setup from
        # base django auth.
        now = timezone.now()
        email = typeclass.objects.normalize_email(email)
        new_account = typeclass(
            username=key,
            email=email,
            is_staff=is_superuser,
            is_superuser=is_superuser,
            last_login=now,
            date_joined=now,
        )
        if password is not None:
            # the password may be None for 'fake' accounts, like bots
            valid, error = new_account.validate_password(password, new_account)
            if not valid:
                raise error

            new_account.set_password(password)

        new_account._createdict = dict(
            locks=locks,
            permissions=permissions,
            report_to=report_to,
            tags=tags,
            attributes=attributes,
        )
        # saving will trigger the signal that calls the
        # at_first_save hook on the typeclass, where the _createdict
        # can be used.
        new_account.save()

        # note that we don't send a signal here, that is sent from the Account.create helper method
        # instead.

        return new_account

    # back-compatibility alias
    account_search = search_account


class AccountManager(AccountDBManager, TypeclassManager):
    pass
