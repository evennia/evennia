import time
from django.utils import timezone
from django.conf import settings

from evennia.commands.cmdsethandler import CmdSetHandler
from evennia import MONITOR_HANDLER

from evennia.server.signals import SIGNAL_ACCOUNT_POST_LOGIN, SIGNAL_ACCOUNT_POST_LOGOUT
from evennia.server.signals import SIGNAL_ACCOUNT_POST_FIRST_LOGIN, SIGNAL_ACCOUNT_POST_LAST_LOGOUT


class EntitySessionHandler:
    """
    Handles adding/removing session references to an Account, Puppet, or perhaps
    stranger things down the line. This is an Abstract Class - inherit from it and
    implement the lower methods. Do not instantiate this directly, it'll error.
    """

    def __init__(self, obj):
        """
        Initializes the handler.
        Args:
            obj (Object): The object on which the handler is defined.
        """
        self.obj = obj
        self._sessions = list()
        self._sessids = dict()

    def all(self, sessid=None):
        """
        Returns all sessions.

        Args:
            sessid (int, optional): Specify a given session by
                session id.
        Returns:
            sessions (list): A list of Session objects. If `sessid`
                is given, this is a list with one (or zero) elements.
        """
        if sessid is None:
            return list(self._sessions)
        found = self._sessids.get(sessid, None)
        if found:
            return [found]
        return []

    # Compatability hack.
    get = all

    def save(self):
        """
        Doesn't do anything on its own. Some things might want to store session ids in the database or something.
        There is no load. There will not be a load.
        """
        pass

    def add(self, session, force=False, sync=False, **kwargs):
        """
        Add session to handler. Do not call this directly - it is meant to be called from
        ServerSession.link(). If this is called directly, ServerSession will not set import attributes.

        Args:
            session (Session or int): Session or session id to add.
            force (bool): Don't stop for anything. Mainly used for Unexpected Disconnects
            sync (bool):

        Returns:
            result (bool): True if success, false if fail.

        Notes:
            We will only add a session/sessid if this actually also exists
            in the core sessionhandler.
        """
        try:
            if session in self._sessions:
                raise ValueError("Session is already linked to this entity!")
            self.validate_link_request(session, force=force, sync=sync, **kwargs)
        except ValueError as e:
            session.msg(e)
            return False
        self.at_before_link_session(session, force=force, sync=sync, **kwargs)
        self._sessions.append(session)
        self._sessids[session.sessid] = session
        self.at_link_session(session, force=force, sync=sync, **kwargs)
        self.at_after_link_session(session, force=force, sync=sync, **kwargs)

        # I really don't know why, but ObjectDB loves to save stuff.
        self.save()
        return True

    def remove(self, session, force=False, reason=None, **kwargs):
        """
        Remove session from handler. As with add(), it must be called by ServerSession.unlink().

        Args:
            session (Session or int): Session or session id to remove.
            force (bool): Don't stop for anything. Mainly used for Unexpected Disconnects
            reason (str or None): A reason that might be displayed down the chain.
        """
        try:
            if session not in self._sessions:
                raise ValueError("Cannot remove session: it is not linked to this object.")
            self.validate_unlink_request(session, force=force, reason=reason, **kwargs)
        except ValueError as e:
            self.obj.msg(e)
            return
        self.at_before_unlink_session(session, force=force, reason=reason, **kwargs)
        self._sessions.remove(session)
        del self._sessids[session.sessid]
        self.at_unlink_session(session, force=force, reason=reason, **kwargs)
        self.at_after_unlink_session(session, force=force, reason=reason, **kwargs)

        # I really don't know why, but ObjectDB loves to save stuff.
        self.save()
        return True

    def count(self):
        """
        Get amount of sessions connected.
        Returns:
            sesslen (int): Number of sessions handled.
        """
        return len(self._sessions)

    def validate_link_request(self, session, force=False, sync=False, **kwargs):
        """
        This is called to check if a Session should be allowed to link this entity.

        Args:
            session (ServerSession): The Session in question.
            force (bool): Bypass most checks for some reason? Usually admin overrides.
            sync (bool): Whether this is operating in sync-after-reload mode.
                In general, nothing should stop it if this is true.

        Raises:
            ValueError(str): An error condition which will prevent the linking.
        """
        raise NotImplementedError()

    def at_before_link_session(self, session, force=False, sync=False, **kwargs):
        """
        This is called to ready an entity for linking. This might do cleanups, kick
        off other Sessions, whatever it needs to do.

        Args:
            session (ServerSession): The Session in question.
            force (bool): Bypass most checks for some reason? Usually admin overrides.
            sync (bool): Whether this is operating in sync-after-reload mode.
                In general, nothing should stop it if this is true.
        """
        raise NotImplementedError()

    def at_link_session(self, session, force=False, sync=False, **kwargs):
        """"
        Sets up our Session connection.
        Args:
            session (ServerSession): The Session in question.
            force (bool): Bypass most checks for some reason? Usually admin overrides.
            sync (bool): Whether this is operating in sync-after-reload mode.
                In general, nothing should stop it if this is true.
        """
        raise NotImplementedError()

    def at_after_link_session(self, session, force=False, sync=False, **kwargs):
        """
        Called just after puppeting has been completed and all
        Account<->Object links have been established.
        Args:
            session (ServerSession): The Session in question.
            force (bool): Bypass most checks for some reason? Usually admin overrides.
            sync (bool): Whether this is operating in sync-after-reload mode.
                In general, nothing should stop it if this is true.
        Note:
            You can use `self.account` and `self.sessions.get()` to get
            account and sessions at this point; the last entry in the
            list from `self.sessions.get()` is the latest Session
            puppeting this Object.
        """
        raise NotImplementedError()

    def validate_unlink_request(self, session, force=False, reason=None, **kwargs):
        """
        Validates an unlink. This can halt an unlink for whatever reason.

        Args:
            session (ServerSession): The session that will be leaving us.
            force (bool): Don't stop for anything. Mainly used for Unexpected Disconnects
            reason (str or None): A reason that might be displayed down the chain.

        Raises:
            ValueError(str): If anything is amiss, raising ValueError will block the
                unlink.
        """
        raise NotImplementedError()

    def at_before_unlink_session(self, session, force=False, reason=None, **kwargs):
        """
        Called just before beginning to un-connect a puppeting from
        this Account.
        Args:
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).
        Note:
            You can use `self.account` and `self.sessions.get()` to get
            account and sessions at this point; the last entry in the
            list from `self.sessions.get()` is the latest Session
            puppeting this Object.
        """
        raise NotImplementedError()

    def at_unlink_session(self, session, force=False, reason=None, **kwargs):
        """
        That's all folks. Disconnect session from this object.

        Args:
            session (ServerSession): The session that will be leaving us.
            force (bool): Don't stop for anything. Mainly used for Unexpected Disconnects
            reason (str or None): A reason that might be displayed down the chain.
        """
        raise NotImplementedError()

    def at_after_unlink_session(self, session, force=False, reason=None, **kwargs):
        """
        Called just after the Account successfully disconnected from
        this object, severing all connections.
        Args:
            account (Account): The account object that just disconnected
                from this object.
            session (Session): Session id controlling the connection that
                just disconnected.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).
        """
        raise NotImplementedError()


class AccountSessionHandler(EntitySessionHandler):

    def validate_link_request(self, session, force=False, sync=False, **kwargs):
        """
        Nothing really to do here. Accounts are validated through their password. That's .authenticate().
        """
        pass

    def at_before_link_session(self, session, force=False, sync=False, **kwargs):
        """
        Implements the Multisession checks. If any conflicting sessions are logged in,
        here we shall force them off.
        """
        existing = self.all()
        self.obj.at_init()
        # Check if this is the first time the *account* logs in
        if self.obj.db.FIRST_LOGIN:
            self.obj.at_first_login()
            del self.obj.db.FIRST_LOGIN

        self.obj.at_pre_login()
        if settings.MULTISESSION_MODE == 0:
            # disconnect all previous sessions.
            session.sessionhandler.disconnect_duplicate_sessions(session)


    def at_link_session(self, session, force=False, sync=False, **kwargs):
        """
        Sets all properties on the Session relevant to this Account.
        """
        session.logged_in = True
        session.account = self.obj
        session.uname = self.obj.username
        session.uid = self.obj.pk
        session.conn_time = time.time()
        session.cmdset_storage = settings.CMDSET_SESSION
        session.cmdset = CmdSetHandler(self.obj, True)

    def at_after_link_session(self, session, force=False, sync=False, **kwargs):
        self.obj.last_login = timezone.now()
        self.obj.save()
        nsess = self.count()
        session.log(f"Logged in: {self.obj} {session.address} ({nsess} session(s) total)")
        self.obj.at_post_login(session=session)
        if nsess < 2:
            SIGNAL_ACCOUNT_POST_FIRST_LOGIN.send(sender=self.obj, session=session)
        SIGNAL_ACCOUNT_POST_LOGIN.send(sender=self.obj, session=session)

    def validate_unlink_request(self, session, force=False, reason=None, **kwargs):
        pass

    def at_before_unlink_session(self, session, force=False, reason=None, **kwargs):
        pass

    def at_unlink_session(self, session, force=False, reason=None, **kwargs):
        session.logged_in = False
        session.uid = None
        session.uname = None
        session.cmdset.add(settings.CMDSET_UNLOGGEDIN, permanent=True, default_cmdset=True)

    def at_after_unlink_session(self, session, force=False, reason=None, **kwargs):
        remaining = self.all()
        if not remaining:
            self.obj.attributes.add(key="last_active_datetime", category="system", value=timezone.now())
            self.obj.is_connected = False
        MONITOR_HANDLER.remove(self.obj, "_saved_webclient_options", session.sessid)

        session.log(f"Logged out: {self.obj} {session.address} ({len(remaining)} sessions(s) remaining)"
                    f"{reason if reason else ''}")

        if not remaining:
            SIGNAL_ACCOUNT_POST_LAST_LOGOUT.send(sender=session.account, session=session)
        SIGNAL_ACCOUNT_POST_LOGOUT.send(sender=session.account, session=session)


class ObjectSessionHandler(EntitySessionHandler):

    def validate_link_request(self, session, force=False, sync=False, **kwargs):
        # We only want to allow puppeting if it's by an authenticated Session
        # that has authority to puppet us!
        if not session.account:
            # not logged in. How did this even happen?
            raise ValueError("You are not logged in to an account!")
        if session.get_puppet() == self:
            # already puppeting this object
            raise ValueError("You are already puppeting this object.")
        if not self.obj.access(session.account, "puppet"):
            # no access
            raise ValueError(f"You don't have permission to puppet '{self.obj.key}'.")
        if self.obj.account and self.obj.account != session.account:
            raise ValueError(f"|c{self.obj.key}|R is already puppeted by another Account.")

    def at_before_link_session_multisession(self, session, force=False, sync=False, **kwargs):
        """
        Multisession logic is performed here. This should not stop the link process.
        """
        # object already puppeted
        # we check for whether it's the same account in a _validate_puppet_request.
        # if we reach here, assume that it's either no account or the same account
        others = self.all()
        if others:
            # we may take over another of our sessions
            # output messages to the affected sessions
            if settings.MULTISESSION_MODE in (1, 3):
                txt1 = f"Sharing |c{self.obj.name}|n with another of your sessions."
                txt2 = f"|c{self.obj.name}|n|G is now shared from another of your sessions.|n"
                session.msg(txt1)
                self.obj.msg(txt2, session=others)
            else:
                txt1 = f"Taking over |c{self.obj.name}|n from another of your sessions."
                txt2 = f"|c{self.obj.name}|n|R is now acted from another of your sessions.|n"
                session.msg(txt1)
                self.obj.msg(txt2, session=others)
                for other in others:
                    other.unlink('puppet', self, force=True, reason="Taken over by another session")

    def at_before_link_session(self, session, force=False, sync=False, **kwargs):
        # First, check multisession status. Kick off anyone as necessary.
        self.at_before_link_session_multisession(session, force, sync, **kwargs)

        if session.puppet:
            # cleanly unpuppet eventual previous object puppeted by this session
            session.unlink('puppet', session.puppet)

        # Call the object at_pre_puppet hook for compatability.
        self.obj.at_pre_puppet(session.account, session, **kwargs)

    def at_link_session(self, session, force=False, sync=False, **kwargs):
        session.puid = self.obj.pk
        session.puppet = self.obj
        self.obj.account = session.account

        # Don't need to validate scripts if there already were sessions attached.
        if not self.count() > 1:
            self.obj.scripts.validate()

        if sync:
            self.obj.locks.cache_lock_bypass(self)

    def at_after_link_session(self, session, force=False, sync=False, **kwargs):
        session.account.db._last_puppet = self.obj

        # call the obj.at_post_puppet hook for compatability.
        self.obj.at_post_puppet(**kwargs)

    def validate_unlink_request(self, session, force=False, reason=None, **kwargs):
        pass

    def at_before_unlink_session(self, session, force=False, reason=None, **kwargs):
        # Calling obj.at_pre_unpuppet() for compatability.
        self.obj.at_pre_unpuppet()

    def at_unlink_session(self, session, force=False, reason=None, **kwargs):
        session.puid = None
        session.puppet = None

        if not self.count():
            self.obj.account = None

    def at_after_unlink_session(self, session, force=False, reason=None, **kwargs):
        # calling obj.at_post_unpuppet() for compatability.
        self.obj.at_post_unpuppet(session.account, session=session, **kwargs)

    def save(self):
        self.obj.db_sessid = ",".join(str(session.sessid) for session in self._sessions if session)
        self.obj.save(update_fields=["db_sessid"])
