"""
Typeclass for Account objects.

Note that this object is primarily intended to
store OOC information, not game info! This
object represents the actual user (not their
character) and has NO actual presence in the
game world (this is handled by the associated
character object, so you should customize that
instead for most things).

"""
import re
import time
from random import getrandbits

from django.conf import settings
from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _

from evennia.accounts.manager import AccountManager
from evennia.accounts.models import AccountDB
from evennia.commands.cmdsethandler import CmdSetHandler
from evennia.comms.models import ChannelDB
from evennia.objects.models import ObjectDB
from evennia.scripts.scripthandler import ScriptHandler
from evennia.server.models import ServerConfig
from evennia.server.signals import (
    SIGNAL_ACCOUNT_POST_CREATE,
    SIGNAL_OBJECT_POST_PUPPET,
    SIGNAL_OBJECT_POST_UNPUPPET,
)
from evennia.server.throttle import Throttle
from evennia.typeclasses.attributes import ModelAttributeBackend, NickHandler
from evennia.typeclasses.models import TypeclassBase
from evennia.utils import class_from_module, create, logger
from evennia.utils.optionhandler import OptionHandler
from evennia.utils.utils import (
    is_iter,
    lazy_property,
    make_iter,
    to_str,
    variable_from_module,
)

__all__ = ("DefaultAccount", "DefaultGuest")

_SESSIONS = None

_AT_SEARCH_RESULT = variable_from_module(*settings.SEARCH_AT_RESULT.rsplit(".", 1))
_MULTISESSION_MODE = settings.MULTISESSION_MODE
_AUTO_CREATE_CHARACTER_WITH_ACCOUNT = settings.AUTO_CREATE_CHARACTER_WITH_ACCOUNT
_AUTO_PUPPET_ON_LOGIN = settings.AUTO_PUPPET_ON_LOGIN
_MAX_NR_SIMULTANEOUS_PUPPETS = settings.MAX_NR_SIMULTANEOUS_PUPPETS
_MAX_NR_CHARACTERS = settings.MAX_NR_CHARACTERS
_CMDSET_ACCOUNT = settings.CMDSET_ACCOUNT
_MUDINFO_CHANNEL = None
_CONNECT_CHANNEL = None
_CMDHANDLER = None


# Create throttles for too many account-creations and login attempts
CREATION_THROTTLE = Throttle(
    name="creation",
    limit=settings.CREATION_THROTTLE_LIMIT,
    timeout=settings.CREATION_THROTTLE_TIMEOUT,
)
LOGIN_THROTTLE = Throttle(
    name="login", limit=settings.LOGIN_THROTTLE_LIMIT, timeout=settings.LOGIN_THROTTLE_TIMEOUT
)


class AccountSessionHandler(object):
    """
    Manages the session(s) attached to an account.

    """

    def __init__(self, account):
        """
        Initializes the handler.

        Args:
            account (Account): The Account on which this handler is defined.

        """
        self.account = account

    def get(self, sessid=None):
        """
        Get the sessions linked to this object.

        Args:
            sessid (int, optional): Specify a given session by
                session id.

        Returns:
            sessions (list): A list of Session objects. If `sessid`
                is given, this is a list with one (or zero) elements.

        """
        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS
        if sessid:
            return make_iter(_SESSIONS.session_from_account(self.account, sessid))
        else:
            return _SESSIONS.sessions_from_account(self.account)

    def all(self):
        """
        Alias to get(), returning all sessions.

        Returns:
            sessions (list): All sessions.

        """
        return self.get()

    def count(self):
        """
        Get amount of sessions connected.

        Returns:
            sesslen (int): Number of sessions handled.

        """
        return len(self.get())


class DefaultAccount(AccountDB, metaclass=TypeclassBase):
    """
    This is the base Typeclass for all Accounts. Accounts represent
    the person playing the game and tracks account info, password
    etc. They are OOC entities without presence in-game. An Account
    can connect to a Character Object in order to "enter" the
    game.

    Account Typeclass API:

    * Available properties (only available on initiated typeclass objects)

     - key (string) - name of account
     - name (string)- wrapper for user.username
     - aliases (list of strings) - aliases to the object. Will be saved to
            database as AliasDB entries but returned as strings.
     - dbref (int, read-only) - unique #id-number. Also "id" can be used.
     - date_created (string) - time stamp of object creation
     - permissions (list of strings) - list of permission strings
     - user (User, read-only) - django User authorization object
     - obj (Object) - game object controlled by account. 'character' can also
                     be used.
     - sessions (list of Sessions) - sessions connected to this account
     - is_superuser (bool, read-only) - if the connected user is a superuser

    * Handlers

     - locks - lock-handler: use locks.add() to add new lock strings
     - db - attribute-handler: store/retrieve database attributes on this
                              self.db.myattr=val, val=self.db.myattr
     - ndb - non-persistent attribute handler: same as db but does not
                                  create a database entry when storing data
     - scripts - script-handler. Add new scripts to object with scripts.add()
     - cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
     - nicks - nick-handler. New nicks with nicks.add().

    * Helper methods

     - msg(text=None, from_obj=None, session=None, options=None, **kwargs)
     - execute_cmd(raw_string)
     - search(ostring, global_search=False, attribute_name=None,
                      use_nicks=False, location=None,
                      ignore_errors=False, account=False)
     - is_typeclass(typeclass, exact=False)
     - swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
     - access(accessing_obj, access_type='read', default=False, no_superuser_bypass=False)
     - check_permstring(permstring)

    * Hook methods

     basetype_setup()
     at_account_creation()

     > note that the following hooks are also found on Objects and are
       usually handled on the character level:

     - at_init()
     - at_access()
     - at_cmdset_get(**kwargs)
     - at_first_login()
     - at_post_login(session=None)
     - at_disconnect()
     - at_message_receive()
     - at_message_send()
     - at_server_reload()
     - at_server_shutdown()

    """

    objects = AccountManager()

    # properties
    @lazy_property
    def cmdset(self):
        return CmdSetHandler(self, True)

    @lazy_property
    def scripts(self):
        return ScriptHandler(self)

    @lazy_property
    def nicks(self):
        return NickHandler(self, ModelAttributeBackend)

    @lazy_property
    def sessions(self):
        return AccountSessionHandler(self)

    @lazy_property
    def options(self):
        return OptionHandler(
            self,
            options_dict=settings.OPTIONS_ACCOUNT_DEFAULT,
            savefunc=self.attributes.add,
            loadfunc=self.attributes.get,
            save_kwargs={"category": "option"},
            load_kwargs={"category": "option"},
        )

    # Do not make this a lazy property; the web UI will not refresh it!
    @property
    def characters(self):
        # Get playable characters list
        objs = self.db._playable_characters or []

        # Rebuild the list if legacy code left null values after deletion
        try:
            if None in objs:
                objs = [x for x in self.db._playable_characters if x]
                self.db._playable_characters = objs
        except Exception as e:
            logger.log_trace(e)
            logger.log_err(e)

        return objs

    def uses_screenreader(self, session=None):
        """
        Shortcut to determine if a session uses a screenreader. If no session given,
        will return true if any of the sessions use a screenreader.

        Args:
            session (Session, optional): The session to check for screen reader.

        """
        if session:
            return bool(session.protocol_flags.get("SCREENREADER", False))
        else:
            return any(
                session.protocol_flags.get("SCREENREADER") for session in self.sessions.all()
            )

    def get_display_name(self, looker, **kwargs):
        """
        This is used by channels and other OOC communications methods to give a
        custom display of this account's input.

        Args:
            looker (Account): The one that will see this name.
            **kwargs: Unused by default, can be used to pass game-specific data.

        Returns:
            str: The name, possibly modified.

        """
        return f"|c{self.key}|n"

    # session-related methods

    def disconnect_session_from_account(self, session, reason=None):
        """
        Access method for disconnecting a given session from the
        account (connection happens automatically in the
        sessionhandler)

        Args:
            session (Session): Session to disconnect.
            reason (str, optional): Eventual reason for the disconnect.

        """
        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS
        _SESSIONS.disconnect(session, reason)

    # puppeting operations

    def puppet_object(self, session, obj):
        """
        Use the given session to control (puppet) the given object (usually
        a Character type).

        Args:
            session (Session): session to use for puppeting
            obj (Object): the object to start puppeting

        Raises:
            RuntimeError: If puppeting is not possible, the
                `exception.msg` will contain the reason.


        """
        # safety checks
        if not obj:
            raise RuntimeError("Object not found")
        if not session:
            raise RuntimeError("Session not found")
        if self.get_puppet(session) == obj:
            # already puppeting this object
            self.msg("You are already puppeting this object.")
            return
        if not obj.access(self, "puppet"):
            # no access
            self.msg(f"You don't have permission to puppet '{obj.key}'.")
            return
        if obj.account:
            # object already puppeted
            if obj.account == self:
                if obj.sessions.count():
                    # we may take over another of our sessions
                    # output messages to the affected sessions
                    if _MULTISESSION_MODE in (1, 3):
                        txt1 = f"Sharing |c{obj.name}|n with another of your sessions."
                        txt2 = f"|c{obj.name}|n|G is now shared from another of your sessions.|n"
                        self.msg(txt1, session=session)
                        self.msg(txt2, session=obj.sessions.all())
                    else:
                        txt1 = f"Taking over |c{obj.name}|n from another of your sessions."
                        txt2 = f"|c{obj.name}|n|R is now acted from another of your sessions.|n"
                        self.msg(txt1, session=session)
                        self.msg(txt2, session=obj.sessions.all())
                        self.unpuppet_object(obj.sessions.get())
            elif obj.account.is_connected:
                # controlled by another account
                self.msg(_("|c{key}|R is already puppeted by another Account.").format(key=obj.key))
                return

        if session.puppet:
            # cleanly unpuppet eventual previous object puppeted by this session
            self.unpuppet_object(session)
        # if we get to this point the character is ready to puppet or it
        # was left with a lingering account/session reference from an unclean
        # server kill or similar

        # check so we are not puppeting too much already
        if _MAX_NR_SIMULTANEOUS_PUPPETS is not None:
            already_puppeted = self.get_all_puppets()
            if (
                not self.is_superuser
                and not self.check_permstring("Developer")
                and obj not in already_puppeted
                and len(self.get_all_puppets()) >= _MAX_NR_SIMULTANEOUS_PUPPETS
            ):
                self.msg(
                    _(f"You cannot control any more puppets (max {_MAX_NR_SIMULTANEOUS_PUPPETS})")
                )
                return

        # do the puppeting
        obj.at_pre_puppet(self, session=session)
        # used to track in case of crash so we can clean up later
        obj.tags.add("puppeted", category="account")

        # do the connection
        obj.sessions.add(session)
        obj.account = self
        session.puid = obj.id
        session.puppet = obj

        # re-cache locks to make sure superuser bypass is updated
        obj.locks.cache_lock_bypass(obj)
        # final hook
        obj.at_post_puppet()
        SIGNAL_OBJECT_POST_PUPPET.send(sender=obj, account=self, session=session)

    def unpuppet_object(self, session):
        """
        Disengage control over an object.

        Args:
            session (Session or list): The session or a list of
                sessions to disengage from their puppets.

        Raises:
            RuntimeError With message about error.

        """
        for session in make_iter(session):
            obj = session.puppet
            if obj:
                # do the disconnect, but only if we are the last session to puppet
                obj.at_pre_unpuppet()
                obj.sessions.remove(session)
                if not obj.sessions.count():
                    del obj.account
                obj.at_post_unpuppet(self, session=session)
                obj.tags.remove("puppeted", category="account")
                SIGNAL_OBJECT_POST_UNPUPPET.send(sender=obj, session=session, account=self)
            # Just to be sure we're always clear.
            session.puppet = None
            session.puid = None

    def unpuppet_all(self):
        """
        Disconnect all puppets. This is called by server before a
        reset/shutdown.
        """
        self.unpuppet_object(self.sessions.all())

    def get_puppet(self, session):
        """
        Get an object puppeted by this session through this account. This is
        the main method for retrieving the puppeted object from the
        account's end.

        Args:
            session (Session): Find puppeted object based on this session

        Returns:
            puppet (Object): The matching puppeted object, if any.

        """
        return session.puppet if session else None

    def get_all_puppets(self):
        """
        Get all currently puppeted objects.

        Returns:
            puppets (list): All puppeted objects currently controlled
                by this Account.

        """
        return list(set(session.puppet for session in self.sessions.all() if session.puppet))

    def __get_single_puppet(self):
        """
        This is a legacy convenience link for use with `MULTISESSION_MODE`.

        Returns:
            puppets (Object or list): Users of `MULTISESSION_MODE` 0 or 1 will
                always get the first puppet back. Users of higher `MULTISESSION_MODE`s will
                get a list of all puppeted objects.

        """
        puppets = self.get_all_puppets()
        if _MULTISESSION_MODE in (0, 1):
            return puppets and puppets[0] or None
        return puppets

    character = property(__get_single_puppet)
    puppet = property(__get_single_puppet)

    # utility methods
    @classmethod
    def is_banned(cls, **kwargs):
        """
        Checks if a given username or IP is banned.

        Keyword Args:
            ip (str, optional): IP address.
            username (str, optional): Username.

        Returns:
            is_banned (bool): Whether either is banned or not.

        """

        ip = kwargs.get("ip", "")
        if isinstance(ip, (tuple, list)):
            ip = ip[0]
        ip = ip.strip()
        username = kwargs.get("username", "").lower().strip()

        # Check IP and/or name bans
        bans = ServerConfig.objects.conf("server_bans")
        if bans and (
            any(tup[0] == username for tup in bans if username)
            or any(tup[2].match(ip) for tup in bans if ip and tup[2])
        ):
            return True

        return False

    @classmethod
    def get_username_validators(
        cls, validator_config=getattr(settings, "AUTH_USERNAME_VALIDATORS", [])
    ):
        """
        Retrieves and instantiates validators for usernames.

        Args:
            validator_config (list): List of dicts comprising the battery of
                validators to apply to a username.

        Returns:
            validators (list): List of instantiated Validator objects.
        """

        objs = []
        for validator in validator_config:
            try:
                klass = import_string(validator["NAME"])
            except ImportError:
                msg = (
                    f"The module in NAME could not be imported: {validator['NAME']}. "
                    "Check your AUTH_USERNAME_VALIDATORS setting."
                )
                raise ImproperlyConfigured(msg)
            objs.append(klass(**validator.get("OPTIONS", {})))
        return objs

    @classmethod
    def authenticate(cls, username, password, ip="", **kwargs):
        """
        Checks the given username/password against the database to see if the
        credentials are valid.

        Note that this simply checks credentials and returns a valid reference
        to the user-- it does not log them in!

        To finish the job:
        After calling this from a Command, associate the account with a Session:
        - session.sessionhandler.login(session, account)

        ...or after calling this from a View, associate it with an HttpRequest:
        - django.contrib.auth.login(account, request)

        Args:
            username (str): Username of account
            password (str): Password of account
            ip (str, optional): IP address of client

        Keyword Args:
            session (Session, optional): Session requesting authentication

        Returns:
            account (DefaultAccount, None): Account whose credentials were
                provided if not banned.
            errors (list): Error messages of any failures.

        """
        errors = []
        if ip:
            ip = str(ip)

        # See if authentication is currently being throttled
        if ip and LOGIN_THROTTLE.check(ip):
            errors.append(_("Too many login failures; please try again in a few minutes."))

            # With throttle active, do not log continued hits-- it is a
            # waste of storage and can be abused to make your logs harder to
            # read and/or fill up your disk.
            return None, errors

        # Check IP and/or name bans
        banned = cls.is_banned(username=username, ip=ip)
        if banned:
            # this is a banned IP or name!
            errors.append(
                _(
                    "|rYou have been banned and cannot continue from here."
                    "\nIf you feel this ban is in error, please email an admin.|x"
                )
            )
            logger.log_sec(f"Authentication Denied (Banned): {username} (IP: {ip}).")
            LOGIN_THROTTLE.update(ip, "Too many sightings of banned artifact.")
            return None, errors

        # Authenticate and get Account object
        account = authenticate(username=username, password=password)
        if not account:
            # User-facing message
            errors.append(_("Username and/or password is incorrect."))

            # Log auth failures while throttle is inactive
            logger.log_sec(f"Authentication Failure: {username} (IP: {ip}).")

            # Update throttle
            if ip:
                LOGIN_THROTTLE.update(ip, _("Too many authentication failures."))

            # Try to call post-failure hook
            session = kwargs.get("session", None)
            if session:
                account = AccountDB.objects.get_account_from_name(username)
                if account:
                    account.at_failed_login(session)

            return None, errors

        # Account successfully authenticated
        logger.log_sec(f"Authentication Success: {account} (IP: {ip}).")
        return account, errors

    @classmethod
    def normalize_username(cls, username):
        """
        Django: Applies NFKC Unicode normalization to usernames so that visually
        identical characters with different Unicode code points are considered
        identical.

        (This deals with the Turkish "i" problem and similar
        annoyances. Only relevant if you go out of your way to allow Unicode
        usernames though-- Evennia accepts ASCII by default.)

        In this case we're simply piggybacking on this feature to apply
        additional normalization per Evennia's standards.
        """
        username = super(DefaultAccount, cls).normalize_username(username)

        # strip excessive spaces in accountname
        username = re.sub(r"\s+", " ", username).strip()

        return username

    @classmethod
    def validate_username(cls, username):
        """
        Checks the given username against the username validator associated with
        Account objects, and also checks the database to make sure it is unique.

        Args:
            username (str): Username to validate

        Returns:
            valid (bool): Whether or not the password passed validation
            errors (list): Error messages of any failures

        """
        valid = []
        errors = []

        # Make sure we're at least using the default validator
        validators = cls.get_username_validators()
        if not validators:
            validators = [cls.username_validator]

        # Try username against all enabled validators
        for validator in validators:
            try:
                valid.append(not validator(username))
            except ValidationError as e:
                valid.append(False)
                errors.extend(e.messages)

        # Disqualify if any check failed
        if False in valid:
            valid = False
        else:
            valid = True

        return valid, errors

    @classmethod
    def validate_password(cls, password, account=None):
        """
        Checks the given password against the list of Django validators enabled
        in the server.conf file.

        Args:
            password (str): Password to validate

        Keyword Args:
            account (DefaultAccount, optional): Account object to validate the
                password for. Optional, but Django includes some validators to
                do things like making sure users aren't setting passwords to the
                same value as their username. If left blank, these user-specific
                checks are skipped.

        Returns:
            valid (bool): Whether or not the password passed validation
            error (ValidationError, None): Any validation error(s) raised. Multiple
                errors can be nested within a single object.

        """
        valid = False
        error = None

        # Validation returns None on success; invert it and return a more sensible bool
        try:
            valid = not password_validation.validate_password(password, user=account)
        except ValidationError as e:
            error = e

        return valid, error

    def set_password(self, password, **kwargs):
        """
        Applies the given password to the account. Logs and triggers the `at_password_change` hook.

        Args:
            password (str): Password to set.

        Notes:
            This is called by Django also when logging in; it should not be mixed up with
            validation, since that would mean old passwords in the database (pre validation checks)
            could get invalidated.

        """
        super().set_password(password)
        logger.log_sec(f"Password successfully changed for {self}.")
        self.at_password_change()

    def create_character(self, *args, **kwargs):
        """
        Create a character linked to this account.

        Args:
            key (str, optional): If not given, use the same name as the account.
            typeclass (str, optional): Typeclass to use for this character. If
                not given, use settings.BASE_CHARACTER_TYPECLASS.
            permissions (list, optional): If not given, use the account's permissions.
            ip (str, optional): The client IP creating this character. Will fall back to the
                one stored for the account if not given.
            kwargs (any): Other kwargs will be used in the create_call.
        Returns:
            Object: A new character of the `character_typeclass` type. None on an error.
            list or None: A list of errors, or None.

        """
        # parse inputs
        character_key = kwargs.pop("key", self.key)
        character_ip = kwargs.pop("ip", self.db.creator_ip)
        character_permissions = kwargs.pop("permissions", self.permissions)

        # Load the appropriate Character class
        character_typeclass = kwargs.pop("typeclass", None)
        character_typeclass = (
            character_typeclass if character_typeclass else settings.BASE_CHARACTER_TYPECLASS
        )
        Character = class_from_module(character_typeclass)

        if "location" not in kwargs:
            kwargs["location"] = ObjectDB.objects.get_id(settings.START_LOCATION)

        # Create the character
        character, errs = Character.create(
            character_key,
            self,
            ip=character_ip,
            typeclass=character_typeclass,
            permissions=character_permissions,
            **kwargs,
        )
        if character:
            # Update playable character list
            if character not in self.characters:
                self.db._playable_characters.append(character)

            # We need to set this to have @ic auto-connect to this character
            self.db._last_puppet = character
        return character, errs

    @classmethod
    def create(cls, *args, **kwargs):
        """
        Creates an Account (or Account/Character pair for MULTISESSION_MODE<2)
        with default (or overridden) permissions and having joined them to the
        appropriate default channels.

        Keyword Args:
            username (str): Username of Account owner
            password (str): Password of Account owner
            email (str, optional): Email address of Account owner
            ip (str, optional): IP address of requesting connection
            guest (bool, optional): Whether or not this is to be a Guest account

            permissions (str, optional): Default permissions for the Account
            typeclass (str, optional): Typeclass to use for new Account
            character_typeclass (str, optional): Typeclass to use for new char
                when applicable.

        Returns:
            account (Account): Account if successfully created; None if not
            errors (list): List of error messages in string form

        """

        account = None
        errors = []

        username = kwargs.get("username")
        password = kwargs.get("password")
        email = kwargs.get("email", "").strip()
        guest = kwargs.get("guest", False)

        permissions = kwargs.get("permissions", settings.PERMISSION_ACCOUNT_DEFAULT)
        typeclass = kwargs.get("typeclass", cls)

        ip = kwargs.get("ip", "")
        if isinstance(ip, (tuple, list)):
            ip = ip[0]

        if ip and CREATION_THROTTLE.check(ip):
            errors.append(
                _("You are creating too many accounts. Please log into an existing account.")
            )
            return None, errors

        # Normalize username
        username = cls.normalize_username(username)

        # Validate username
        if not guest:
            valid, errs = cls.validate_username(username)
            if not valid:
                # this echoes the restrictions made by django's auth
                # module (except not allowing spaces, for convenience of
                # logging in).
                errors.extend(errs)
                return None, errors

        # Validate password
        # Have to create a dummy Account object to check username similarity
        valid, errs = cls.validate_password(password, account=cls(username=username))
        if not valid:
            errors.extend(errs)
            return None, errors

        # Check IP and/or name bans
        banned = cls.is_banned(username=username, ip=ip)
        if banned:
            # this is a banned IP or name!
            string = _(
                "|rYou have been banned and cannot continue from here."
                "\nIf you feel this ban is in error, please email an admin.|x"
            )
            errors.append(string)
            return None, errors

        # everything's ok. Create the new account.
        try:
            try:
                account = create.create_account(
                    username, email, password, permissions=permissions, typeclass=typeclass
                )
                logger.log_sec(f"Account Created: {account} (IP: {ip}).")

            except Exception:
                errors.append(
                    _(
                        "There was an error creating the Account. "
                        "If this problem persists, contact an admin."
                    )
                )
                logger.log_trace()
                return None, errors

            # This needs to be set so the engine knows this account is
            # logging in for the first time. (so it knows to call the right
            # hooks during login later)
            account.db.FIRST_LOGIN = True

            # Record IP address of creation, if available
            if ip:
                account.db.creator_ip = ip

            # join the new account to the public channel
            pchannel = ChannelDB.objects.get_channel(settings.DEFAULT_CHANNELS[0]["key"])
            if not pchannel or not pchannel.connect(account):
                string = "New account '{account.key}' could not connect to public channel!"
                errors.append(string)
                logger.log_err(string)

            if account and _AUTO_CREATE_CHARACTER_WITH_ACCOUNT:
                # Auto-create a character to go with this account

                character, errs = account.create_character(
                    typeclass=kwargs.get("character_typeclass")
                )
                if errs:
                    errors.extend(errs)

        except Exception:
            # We are in the middle between logged in and -not, so we have
            # to handle tracebacks ourselves at this point. If we don't,
            # we won't see any errors at all.
            errors.append(_("An error occurred. Please e-mail an admin if the problem persists."))
            logger.log_trace()

        # Update the throttle to indicate a new account was created from this IP
        if ip and not guest:
            CREATION_THROTTLE.update(ip, "Too many accounts being created.")
        SIGNAL_ACCOUNT_POST_CREATE.send(sender=account, ip=ip)
        return account, errors

    def delete(self, *args, **kwargs):
        """
        Deletes the account persistently.

        Notes:
            `*args` and `**kwargs` are passed on to the base delete
             mechanism (these are usually not used).

        Return:
            bool: If deletion was successful. Only time it fails would be
                if the Account was already deleted. Note that even on a failure,
                connected resources (nicks/aliases etc) will still have been
                deleted.

        """
        for session in self.sessions.all():
            # unpuppeting all objects and disconnecting the user, if any
            # sessions remain (should usually be handled from the
            # deleting command)
            try:
                self.unpuppet_object(session)
            except RuntimeError:
                # no puppet to disconnect from
                pass
            session.sessionhandler.disconnect(session, reason=_("Account being deleted."))
        self.scripts.stop()
        self.attributes.clear()
        self.nicks.clear()
        self.aliases.clear()
        if not self.pk:
            return False
        super().delete(*args, **kwargs)
        return True

    # methods inherited from database model

    def msg(self, text=None, from_obj=None, session=None, options=None, **kwargs):
        """
        Evennia -> User
        This is the main route for sending data back to the user from the
        server.

        Args:
            text (str or tuple, optional): The message to send. This
                is treated internally like any send-command, so its
                value can be a tuple if sending multiple arguments to
                the `text` oob command.
            from_obj (Object or Account or list, optional): Object sending. If given, its
                at_msg_send() hook will be called. If iterable, call on all entities.
            session (Session or list, optional): Session object or a list of
                Sessions to receive this send. If given, overrules the
                default send behavior for the current
                MULTISESSION_MODE.
            options (list): Protocol-specific options. Passed on to the protocol.
        Keyword Args:
            any (dict): All other keywords are passed on to the protocol.

        """
        if from_obj:
            # call hook
            for obj in make_iter(from_obj):
                try:
                    obj.at_msg_send(text=text, to_obj=self, **kwargs)
                except Exception:
                    # this may not be assigned.
                    logger.log_trace()
        try:
            if not self.at_msg_receive(text=text, **kwargs):
                # abort message to this account
                return
        except Exception:
            # this may not be assigned.
            pass

        kwargs["options"] = options

        if text is not None:
            if not (isinstance(text, str) or isinstance(text, tuple)):
                # sanitize text before sending across the wire
                try:
                    text = to_str(text)
                except Exception:
                    text = repr(text)
            kwargs["text"] = text

        # session relay
        sessions = make_iter(session) if session else self.sessions.all()
        for session in sessions:
            session.data_out(**kwargs)

    def execute_cmd(self, raw_string, session=None, **kwargs):
        """
        Do something as this account. This method is never called normally,
        but only when the account object itself is supposed to execute the
        command. It takes account nicks into account, but not nicks of
        eventual puppets.

        Args:
            raw_string (str): Raw command input coming from the command line.
            session (Session, optional): The session to be responsible
                for the command-send

        Keyword Args:
            kwargs (any): Other keyword arguments will be added to the
                found command object instance as variables before it
                executes. This is unused by default Evennia but may be
                used to set flags and change operating parameters for
                commands at run-time.

        """
        # break circular import issues
        global _CMDHANDLER
        if not _CMDHANDLER:
            from evennia.commands.cmdhandler import cmdhandler as _CMDHANDLER
        raw_string = self.nicks.nickreplace(
            raw_string, categories=("inputline", "channel"), include_account=False
        )
        if not session and _MULTISESSION_MODE in (0, 1):
            # for these modes we use the first/only session
            sessions = self.sessions.get()
            session = sessions[0] if sessions else None

        return _CMDHANDLER(self, raw_string, callertype="account", session=session, **kwargs)

    # channel receive hooks

    def at_pre_channel_msg(self, message, channel, senders=None, **kwargs):
        """
        Called by the Channel just before passing a message into `channel_msg`.
        This allows for tweak messages per-user and also to abort the
        receive on the receiver-level.

        Args:
            message (str): The message sent to the channel.
            channel (Channel): The sending channel.
            senders (list, optional): Accounts or Objects acting as senders.
                For most normal messages, there is only a single sender. If
                there are no senders, this may be a broadcasting message.
            **kwargs: These are additional keywords passed into `channel_msg`.
                If `no_prefix=True` or `emit=True` are passed, the channel
                prefix will not be added (`[channelname]: ` by default)

        Returns:
            str or None: Allows for customizing the message for this recipient.
                If returning `None` (or `False`) message-receiving is aborted.
                The returning string will be passed into `self.channel_msg`.

        Notes:
            This support posing/emotes by starting channel-send with : or ;.

        """
        if senders:
            sender_string = ", ".join(sender.get_display_name(self) for sender in senders)
            message_lstrip = message.lstrip()
            if message_lstrip.startswith((":", ";")):
                # this is a pose, should show as e.g. "User1 smiles to channel"
                spacing = "" if message_lstrip[1:].startswith((":", "'", ",")) else " "
                message = f"{sender_string}{spacing}{message_lstrip[1:]}"
            else:
                # normal message
                message = f"{sender_string}: {message}"

        if not kwargs.get("no_prefix") and not kwargs.get("emit"):
            message = channel.channel_prefix() + message

        return message

    def channel_msg(self, message, channel, senders=None, **kwargs):
        """
        This performs the actions of receiving a message to an un-muted
        channel.

        Args:
            message (str): The message sent to the channel.
            channel (Channel): The sending channel.
            senders (list, optional): Accounts or Objects acting as senders.
                For most normal messages, there is only a single sender. If
                there are no senders, this may be a broadcasting message or
                similar.
            **kwargs: These are additional keywords originally passed into
                `Channel.msg`.

        Notes:
            Before this, `Channel.at_pre_channel_msg` will fire, which offers a way
            to customize the message for the receiver on the channel-level.

        """
        self.msg(
            text=(message, {"from_channel": channel.id}),
            from_obj=senders,
            options={"from_channel": channel.id},
        )

    def at_post_channel_msg(self, message, channel, senders=None, **kwargs):
        """
        Called by `self.channel_msg` after message was received.

        Args:
            message (str): The message sent to the channel.
            channel (Channel): The sending channel.
            senders (list, optional): Accounts or Objects acting as senders.
                For most normal messages, there is only a single sender. If
                there are no senders, this may be a broadcasting message.
            **kwargs: These are additional keywords passed into `channel_msg`.

        """
        pass

    # search method

    def search(
        self,
        searchdata,
        return_puppet=False,
        search_object=False,
        typeclass=None,
        nofound_string=None,
        multimatch_string=None,
        use_nicks=True,
        quiet=False,
        **kwargs,
    ):
        """
        This is similar to `DefaultObject.search` but defaults to searching
        for Accounts only.

        Args:
            searchdata (str or int): Search criterion, the Account's
                key or dbref to search for.
            return_puppet (bool, optional): Instructs the method to
                return matches as the object the Account controls rather
                than the Account itself (or None) if nothing is puppeted).
            search_object (bool, optional): Search for Objects instead of
                Accounts. This is used by e.g. the @examine command when
                wanting to examine Objects while OOC.
            typeclass (Account typeclass, optional): Limit the search
                only to this particular typeclass. This can be used to
                limit to specific account typeclasses or to limit the search
                to a particular Object typeclass if `search_object` is True.
            nofound_string (str, optional): A one-time error message
                to echo if `searchdata` leads to no matches. If not given,
                will fall back to the default handler.
            multimatch_string (str, optional): A one-time error
                message to echo if `searchdata` leads to multiple matches.
                If not given, will fall back to the default handler.
            use_nicks (bool, optional): Use account-level nick replacement.
            quiet (bool, optional): If set, will not show any error to the user,
                and will also lead to returning a list of matches.

        Return:
            match (Account, Object or None): A single Account or Object match.
            list: If `quiet=True` this is a list of 0, 1 or more Account or Object matches.

        Notes:
            Extra keywords are ignored, but are allowed in call in
            order to make API more consistent with
            objects.objects.DefaultObject.search.

        """
        # handle me, self and *me, *self
        if isinstance(searchdata, str):
            # handle wrapping of common terms
            if searchdata.lower() in ("me", "*me", "self", "*self"):
                return self
        searchdata = self.nicks.nickreplace(
            searchdata, categories=("account",), include_account=False
        )
        if search_object:
            matches = ObjectDB.objects.object_search(searchdata, typeclass=typeclass)
        else:
            matches = AccountDB.objects.account_search(searchdata, typeclass=typeclass)

        if quiet:
            matches = list(matches)
            if return_puppet:
                matches = [match.puppet for match in matches]
        else:
            matches = _AT_SEARCH_RESULT(
                matches,
                self,
                query=searchdata,
                nofound_string=nofound_string,
                multimatch_string=multimatch_string,
            )
            if matches and return_puppet:
                try:
                    matches = matches.puppet
                except AttributeError:
                    return None
        return matches

    def access(
        self, accessing_obj, access_type="read", default=False, no_superuser_bypass=False, **kwargs
    ):
        """
        Determines if another object has permission to access this
        object in whatever way.

        Args:
          accessing_obj (Object): Object trying to access this one.
          access_type (str, optional): Type of access sought.
          default (bool, optional): What to return if no lock of
            access_type was found
          no_superuser_bypass (bool, optional): Turn off superuser
            lock bypassing. Be careful with this one.

        Keyword Args:
          kwargs (any): Passed to the at_access hook along with the result.

        Returns:
            result (bool): Result of access check.

        """
        result = super().access(
            accessing_obj,
            access_type=access_type,
            default=default,
            no_superuser_bypass=no_superuser_bypass,
        )
        self.at_access(result, accessing_obj, access_type, **kwargs)
        return result

    @property
    def idle_time(self):
        """
        Returns the idle time of the least idle session in seconds. If
        no sessions are connected it returns nothing.
        """
        idle = [session.cmd_last_visible for session in self.sessions.all()]
        if idle:
            return time.time() - float(max(idle))
        return None

    @property
    def connection_time(self):
        """
        Returns the maximum connection time of all connected sessions
        in seconds. Returns nothing if there are no sessions.
        """
        conn = [session.conn_time for session in self.sessions.all()]
        if conn:
            return time.time() - float(min(conn))
        return None

    # account hooks

    def basetype_setup(self):
        """
        This sets up the basic properties for an account. Overload this
        with at_account_creation rather than changing this method.

        """
        # A basic security setup
        lockstring = (
            "examine:perm(Admin);edit:perm(Admin);"
            "delete:perm(Admin);boot:perm(Admin);msg:all();"
            "noidletimeout:perm(Builder) or perm(noidletimeout)"
        )
        self.locks.add(lockstring)

        # The ooc account cmdset
        self.cmdset.add_default(_CMDSET_ACCOUNT, persistent=True)

    def at_account_creation(self):
        """
        This is called once, the very first time the account is created
        (i.e. first time they register with the game). It's a good
        place to store attributes all accounts should have, like
        configuration values etc.

        """
        # set an (empty) attribute holding the characters this account has
        lockstring = "attrread:perm(Admins);attredit:perm(Admins);attrcreate:perm(Admins);"
        self.attributes.add("_playable_characters", [], lockstring=lockstring)
        self.attributes.add("_saved_protocol_flags", {}, lockstring=lockstring)

    def at_init(self):
        """
        This is always called whenever this object is initiated --
        that is, whenever it its typeclass is cached from memory. This
        happens on-demand first time the object is used or activated
        in some way after being created but also after each server
        restart or reload. In the case of account objects, this usually
        happens the moment the account logs in or reconnects after a
        reload.

        """
        pass

    # Note that the hooks below also exist in the character object's
    # typeclass. You can often ignore these and rely on the character
    # ones instead, unless you are implementing a multi-character game
    # and have some things that should be done regardless of which
    # character is currently connected to this account.

    def at_first_save(self):
        """
        This is a generic hook called by Evennia when this object is
        saved to the database the very first time.  You generally
        don't override this method but the hooks called by it.

        """
        self.basetype_setup()
        self.at_account_creation()
        # initialize Attribute/TagProperties
        self.init_evennia_properties()

        permissions = [settings.PERMISSION_ACCOUNT_DEFAULT]
        if hasattr(self, "_createdict"):
            # this will only be set if the utils.create_account
            # function was used to create the object.
            cdict = self._createdict
            updates = []
            if not cdict.get("key"):
                if not self.db_key:
                    self.db_key = f"#{self.dbid}"
                    updates.append("db_key")
            elif self.key != cdict.get("key"):
                updates.append("db_key")
                self.db_key = cdict["key"]
            if updates:
                self.save(update_fields=updates)

            if cdict.get("locks"):
                self.locks.add(cdict["locks"])
            if cdict.get("permissions"):
                permissions = cdict["permissions"]
            if cdict.get("tags"):
                # this should be a list of tags, tuples (key, category) or (key, category, data)
                self.tags.batch_add(*cdict["tags"])
            if cdict.get("attributes"):
                # this should be tuples (key, val, ...)
                self.attributes.batch_add(*cdict["attributes"])
            if cdict.get("nattributes"):
                # this should be a dict of nattrname:value
                for key, value in cdict["nattributes"]:
                    self.nattributes.add(key, value)
            del self._createdict

        self.permissions.batch_add(*permissions)

    def at_access(self, result, accessing_obj, access_type, **kwargs):
        """
        This is triggered after an access-call on this Account has
            completed.

        Args:
            result (bool): The result of the access check.
            accessing_obj (any): The object requesting the access
                check.
            access_type (str): The type of access checked.

        Keyword Args:
            kwargs (any): These are passed on from the access check
                and can be used to relay custom instructions from the
                check mechanism.

        Notes:
            This method cannot affect the result of the lock check and
            its return value is not used in any way. It can be used
            e.g.  to customize error messages in a central location or
            create other effects based on the access result.

        """
        pass

    def at_cmdset_get(self, **kwargs):
        """
        Called just *before* cmdsets on this account are requested by
        the command handler. The cmdsets are available as
        `self.cmdset`. If changes need to be done on the fly to the
        cmdset before passing them on to the cmdhandler, this is the
        place to do it.  This is called also if the account currently
        have no cmdsets. kwargs are usually not used unless the
        cmdset is generated dynamically.

        """
        pass

    def at_first_login(self, **kwargs):
        """
        Called the very first time this account logs into the game.
        Note that this is called *before* at_pre_login, so no session
        is established and usually no character is yet assigned at
        this point. This hook is intended for account-specific setup
        like configurations.

        Args:
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def at_password_change(self, **kwargs):
        """
        Called after a successful password set/modify.

        Args:
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def at_pre_login(self, **kwargs):
        """
        Called every time the user logs in, just before the actual
        login-state is set.

        Args:
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def _send_to_connect_channel(self, message):
        """
        Helper method for loading and sending to the comm channel dedicated to
        connection messages. This will also be sent to the mudinfo channel.

        Args:
            message (str): A message to send to the connect channel.

        """
        global _MUDINFO_CHANNEL, _CONNECT_CHANNEL
        if _MUDINFO_CHANNEL is None:
            if settings.CHANNEL_MUDINFO:
                try:
                    _MUDINFO_CHANNEL = ChannelDB.objects.get(db_key=settings.CHANNEL_MUDINFO["key"])
                except ChannelDB.DoesNotExist:
                    logger.log_trace()
            else:
                _MUDINFO = False
        if _CONNECT_CHANNEL is None:
            if settings.CHANNEL_CONNECTINFO:
                try:
                    _CONNECT_CHANNEL = ChannelDB.objects.get(
                        db_key=settings.CHANNEL_CONNECTINFO["key"]
                    )
                except ChannelDB.DoesNotExist:
                    logger.log_trace()
            else:
                _CONNECT_CHANNEL = False

        if settings.USE_TZ:
            now = timezone.localtime()
        else:
            now = timezone.now()
        now = "%02i-%02i-%02i(%02i:%02i)" % (now.year, now.month, now.day, now.hour, now.minute)
        if _MUDINFO_CHANNEL:
            _MUDINFO_CHANNEL.msg(f"[{now}]: {message}")
        if _CONNECT_CHANNEL:
            _CONNECT_CHANNEL.msg(f"[{now}]: {message}")

    def at_post_login(self, session=None, **kwargs):
        """
        Called at the end of the login process, just before letting
        the account loose.

        Args:
            session (Session, optional): Session logging in, if any.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:
            This is called *before* an eventual Character's
            `at_post_login` hook. By default it is used to set up
            auto-puppeting based on `MULTISESSION_MODE`

        """
        # if we have saved protocol flags on ourselves, load them here.
        protocol_flags = self.attributes.get("_saved_protocol_flags", {})
        if session and protocol_flags:
            session.update_flags(**protocol_flags)

        # inform the client that we logged in through an OOB message
        if session:
            session.msg(logged_in={})

        self._send_to_connect_channel(_("|G{key} connected|n").format(key=self.key))
        if _AUTO_PUPPET_ON_LOGIN:
            # in this mode we try to auto-connect to our last connected object, if any
            try:
                self.puppet_object(session, self.db._last_puppet)
            except RuntimeError:
                self.msg(_("The Character does not exist."))
                return
        else:
            # In this mode we don't auto-connect but by default end up at a character selection
            # screen. We execute look on the account.
            # we make sure to clean up the _playable_characters list in case
            # any was deleted in the interim.
            self.db._playable_characters = [char for char in self.db._playable_characters if char]
            self.msg(
                self.at_look(target=self.db._playable_characters, session=session), session=session
            )

    def at_failed_login(self, session, **kwargs):
        """
        Called by the login process if a user account is targeted correctly
        but provided with an invalid password. By default it does nothing,
        but exists to be overridden.

        Args:
            session (session): Session logging in.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).
        """
        pass

    def at_disconnect(self, reason=None, **kwargs):
        """
        Called just before user is disconnected.

        Args:
            reason (str, optional): The reason given for the disconnect,
                (echoed to the connection channel by default).
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).


        """
        reason = f" ({reason if reason else ''})"
        self._send_to_connect_channel(
            _("|R{key} disconnected{reason}|n").format(key=self.key, reason=reason)
        )

    def at_post_disconnect(self, **kwargs):
        """
        This is called *after* disconnection is complete. No messages
        can be relayed to the account from here. After this call, the
        account should not be accessed any more, making this a good
        spot for deleting it (in the case of a guest account account,
        for example).

        Args:
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        pass

    def at_msg_receive(self, text=None, from_obj=None, **kwargs):
        """
        This hook is called whenever someone sends a message to this
        object using the `msg` method.

        Note that from_obj may be None if the sender did not include
        itself as an argument to the obj.msg() call - so you have to
        check for this. .

        Consider this a pre-processing method before msg is passed on
        to the user session. If this method returns False, the msg
        will not be passed on.

        Args:
            text (str, optional): The message received.
            from_obj (any, optional): The object sending the message.

        Keyword Args:
            This includes any keywords sent to the `msg` method.

        Returns:
            receive (bool): If this message should be received.

        Notes:
            If this method returns False, the `msg` operation
            will abort without sending the message.

        """
        return True

    def at_msg_send(self, text=None, to_obj=None, **kwargs):
        """
        This is a hook that is called when *this* object sends a
        message to another object with `obj.msg(text, to_obj=obj)`.

        Args:
            text (str, optional): Text to send.
            to_obj (any, optional): The object to send to.

        Keyword Args:
            Keywords passed from msg()

        Notes:
            Since this method is executed by `from_obj`, if no `from_obj`
            was passed to `DefaultCharacter.msg` this hook will never
            get called.

        """
        pass

    def at_server_reload(self):
        """
        This hook is called whenever the server is shutting down for
        restart/reboot. If you want to, for example, save
        non-persistent properties across a restart, this is the place
        to do it.
        """
        pass

    def at_server_shutdown(self):
        """
        This hook is called whenever the server is shutting down fully
        (i.e. not for a restart).
        """
        pass

    ooc_appearance_template = """
--------------------------------------------------------------------
{header}

{sessions}

  |whelp|n - more commands
  |wpublic <text>|n - talk on public channel
  |wcharcreate <name> [=description]|n - create new character
  |wchardelete <name>|n - delete a character
  |wic <name>|n - enter the game as character (|wooc|n to get back here)
  |wic|n - enter the game as latest character controlled.

{characters}
{footer}
--------------------------------------------------------------------
""".strip()

    def at_look(self, target=None, session=None, **kwargs):
        """
        Called when this object executes a look. It allows to customize
        just what this means.

        Args:
            target (Object or list, optional): An object or a list
                objects to inspect. This is normally a list of characters.
            session (Session, optional): The session doing this look.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            look_string (str): A prepared look string, ready to send
                off to any recipient (usually to ourselves)

        """

        if target and not is_iter(target):
            # single target - just show it
            if hasattr(target, "return_appearance"):
                return target.return_appearance(self)
            else:
                return f"{target} has no in-game appearance."

        # multiple targets - this is a list of characters
        characters = list(tar for tar in target if tar) if target else []
        ncars = len(characters)
        sessions = self.sessions.all()
        nsess = len(sessions)

        if not nsess:
            # no sessions, nothing to report
            return ""

        # header text
        txt_header = f"Account |g{self.name}|n (you are Out-of-Character)"

        # sessions
        sess_strings = []
        for isess, sess in enumerate(sessions):
            ip_addr = sess.address[0] if isinstance(sess.address, tuple) else sess.address
            addr = f"{sess.protocol_key} ({ip_addr})"
            sess_str = (
                f"|w* {isess + 1}|n"
                if session and session.sessid == sess.sessid
                else f"  {isess + 1}"
            )

            sess_strings.append(f"{sess_str} {addr}")

        txt_sessions = "|wConnected session(s):|n\n" + "\n".join(sess_strings)

        if not characters:
            txt_characters = "You don't have a character yet. Use |wcharcreate|n."
        else:
            max_chars = (
                "unlimited"
                if self.is_superuser or _MAX_NR_CHARACTERS is None
                else _MAX_NR_CHARACTERS
            )

            char_strings = []
            for char in characters:
                csessions = char.sessions.all()
                if csessions:
                    for sess in csessions:
                        # character is already puppeted
                        sid = sess in sessions and sessions.index(sess) + 1
                        if sess and sid:
                            char_strings.append(
                                f" - |G{char.name}|n [{', '.join(char.permissions.all())}] "
                                f"(played by you in session {sid})"
                            )
                        else:
                            char_strings.append(
                                f" - |R{char.name}|n [{', '.join(char.permissions.all())}] "
                                "(played by someone else)"
                            )
                else:
                    # character is "free to puppet"
                    char_strings.append(f" - {char.name} [{', '.join(char.permissions.all())}]")

            txt_characters = (
                f"Available character(s) ({ncars}/{max_chars}, |wic <name>|n to play):|n\n"
                + "\n".join(char_strings)
            )
        return self.ooc_appearance_template.format(
            header=txt_header,
            sessions=txt_sessions,
            characters=txt_characters,
            footer="",
        )


class DefaultGuest(DefaultAccount):
    """
    This class is used for guest logins. Unlike Accounts, Guests and
    their characters are deleted after disconnection.

    """

    @classmethod
    def create(cls, **kwargs):
        """
        Forwards request to cls.authenticate(); returns a DefaultGuest object
        if one is available for use.

        """
        return cls.authenticate(**kwargs)

    @classmethod
    def authenticate(cls, **kwargs):
        """
        Gets or creates a Guest account object.

        Keyword Args:
            ip (str, optional): IP address of requester; used for ban checking,
                throttling and logging

        Returns:
            account (Object): Guest account object, if available
            errors (list): List of error messages accrued during this request.

        """
        errors = []
        account = None
        username = None
        ip = kwargs.get("ip", "").strip()

        # check if guests are enabled.
        if not settings.GUEST_ENABLED:
            errors.append(_("Guest accounts are not enabled on this server."))
            return None, errors

        try:
            # Find an available guest name.
            for name in settings.GUEST_LIST:
                if not AccountDB.objects.filter(username__iexact=name).exists():
                    username = name
                    break
            if not username:
                errors.append(_("All guest accounts are in use. Please try again later."))
                if ip:
                    LOGIN_THROTTLE.update(ip, "Too many requests for Guest access.")
                return None, errors
            else:
                # build a new account with the found guest username
                password = "%016x" % getrandbits(64)
                home = settings.GUEST_HOME
                permissions = settings.PERMISSION_GUEST_DEFAULT
                typeclass = settings.BASE_GUEST_TYPECLASS

                # Call parent class creator
                account, errs = super(DefaultGuest, cls).create(
                    guest=True,
                    username=username,
                    password=password,
                    permissions=permissions,
                    typeclass=typeclass,
                    home=home,
                    ip=ip,
                )
                errors.extend(errs)

                if not account.characters:
                    # this can happen for multisession_mode > 1. For guests we
                    # always auto-create a character, regardless of multi-session-mode.
                    character, errs = account.create_character()

                if errs:
                    errors.extend(errs)

                return account, errors

        except Exception:
            # We are in the middle between logged in and -not, so we have
            # to handle tracebacks ourselves at this point. If we don't,
            # we won't see any errors at all.
            errors.append(_("An error occurred. Please e-mail an admin if the problem persists."))
            logger.log_trace()
            return None, errors

        return account, errors

    def at_post_login(self, session=None, **kwargs):
        """
        By default, Guests only have one character regardless of which
        MAX_NR_CHARACTERS we use. They also always auto-puppet a matching
        character and don't get a choice.

        Args:
            session (Session, optional): Session connecting.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        self._send_to_connect_channel(_("|G{key} connected|n").format(key=self.key))
        self.puppet_object(session, self.db._last_puppet)

    def at_server_shutdown(self):
        """
        We repeat the functionality of `at_disconnect()` here just to
        be on the safe side.
        """
        super().at_server_shutdown()
        characters = self.db._playable_characters
        if characters:
            for character in characters:
                if character:
                    character.delete()

    def at_post_disconnect(self, **kwargs):
        """
        Once having disconnected, destroy the guest's characters and

        Args:
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        super().at_post_disconnect()
        characters = self.db._playable_characters
        for character in characters:
            if character:
                character.delete()
        self.delete()
