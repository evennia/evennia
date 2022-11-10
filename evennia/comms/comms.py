"""
Base typeclass for in-game Channels.

"""
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.text import slugify

from evennia.comms.managers import ChannelManager
from evennia.comms.models import ChannelDB
from evennia.typeclasses.models import TypeclassBase
from evennia.utils import create, logger
from evennia.utils.utils import make_iter


class DefaultChannel(ChannelDB, metaclass=TypeclassBase):
    """
    This is the base class for all Channel Comms. Inherit from this to
    create different types of communication channels.

    Class-level variables:
    - `send_to_online_only` (bool, default True) - if set, will only try to
      send to subscribers that are actually active. This is a useful optimization.
    - `log_file` (str, default `"channel_{channelname}.log"`). This is the
      log file to which the channel history will be saved. The `{channelname}` tag
      will be replaced by the key of the Channel. If an Attribute 'log_file'
      is set, this will be used instead. If this is None and no Attribute is found,
      no history will be saved.
    - `channel_prefix_string` (str, default `"[{channelname} ]"`) - this is used
      as a simple template to get the channel prefix with `.channel_prefix()`. It is used
      in front of every channel message; use `{channelmessage}` token to insert the
      name of the current channel. Set to `None` if you want no prefix (or want to
      handle it in a hook during message generation instead.
    - `channel_msg_nick_pattern`(str, default `"{alias}\\s*?|{alias}\\s+?(?P<arg1>.+?)") -
      this is what used when a channel subscriber gets a channel nick assigned to this
      channel. The nickhandler uses the pattern to pick out this channel's name from user
      input. The `{alias}` token will get both the channel's key and any set/custom aliases
      per subscriber. You need to allow for an `<arg1>` regex group to catch any message
      that should be send to the  channel. You usually don't need to change this pattern
      unless you are changing channel command-style entirely.
    - `channel_msg_nick_replacement` (str, default `"channel {channelname} = $1"` - this
      is used by the nickhandler to generate a replacement string once the nickhandler (using
      the `channel_msg_nick_pattern`) identifies that the channel should be addressed
      to send a message to it. The `<arg1>` regex pattern match from `channel_msg_nick_pattern`
      will end up at the `$1` position in the replacement. Together, this allows you do e.g.
      'public Hello' and have that become a mapping to `channel public = Hello`. By default,
      the account-level `channel` command is used. If you were to rename that command you must
      tweak the output to something like `yourchannelcommandname {channelname} = $1`.

    """

    objects = ChannelManager()

    # channel configuration

    # only send to characters/accounts who has an active session (this is a
    # good optimization since people can still recover history separately).
    send_to_online_only = True
    # store log in log file. `channel_key tag will be replace with key of channel.
    # Will use log_file Attribute first, if given
    log_file = "channel_{channelname}.log"
    # which prefix to use when showing were a message is coming from. Set to
    # None to disable and set this later.
    channel_prefix_string = "[{channelname}] "

    # default nick-alias replacements (default using the 'channel' command)
    channel_msg_nick_pattern = r"{alias}\s*?|{alias}\s+?(?P<arg1>.+?)"
    channel_msg_nick_replacement = "channel {channelname} = $1"

    def at_first_save(self):
        """
        Called by the typeclass system the very first time the channel
        is saved to the database. Generally, don't overload this but
        the hooks called by this method.

        """
        self.basetype_setup()
        self.at_channel_creation()
        # initialize Attribute/TagProperties
        self.init_evennia_properties()

        if hasattr(self, "_createdict"):
            # this is only set if the channel was created
            # with the utils.create.create_channel function.
            cdict = self._createdict
            if not cdict.get("key"):
                if not self.db_key:
                    self.db_key = "#i" % self.dbid
            elif cdict["key"] and self.key != cdict["key"]:
                self.key = cdict["key"]
            if cdict.get("aliases"):
                self.aliases.add(cdict["aliases"])
            if cdict.get("locks"):
                self.locks.add(cdict["locks"])
            if cdict.get("keep_log"):
                self.attributes.add("keep_log", cdict["keep_log"])
            if cdict.get("desc"):
                self.attributes.add("desc", cdict["desc"])
            if cdict.get("tags"):
                self.tags.batch_add(*cdict["tags"])

    def basetype_setup(self):
        self.locks.add("send:all();listen:all();control:perm(Admin)")

        # make sure we don't have access to a same-named old channel's history.
        log_file = self.get_log_filename()
        logger.rotate_log_file(log_file, num_lines_to_append=0)

    def at_channel_creation(self):
        """
        Called once, when the channel is first created.

        """
        pass

    # helper methods, for easy overloading

    _log_file = None

    def get_log_filename(self):
        """
        File name to use for channel log.

        Returns:
            str: The filename to use (this is always assumed to be inside
                settings.LOG_DIR)

        """
        if not self._log_file:
            self._log_file = self.attributes.get(
                "log_file", self.log_file.format(channelname=self.key.lower())
            )
        return self._log_file

    def set_log_filename(self, filename):
        """
        Set a custom log filename.

        Args:
            filename (str): The filename to set. This is a path starting from
                inside the settings.LOG_DIR location.

        """
        self.attributes.add("log_file", filename)

    def has_connection(self, subscriber):
        """
        Checks so this account is actually listening
        to this channel.

        Args:
            subscriber (Account or Object): Entity to check.

        Returns:
            has_sub (bool): Whether the subscriber is subscribing to
                this channel or not.

        Notes:
            This will first try Account subscribers and only try Object
                if the Account fails.

        """
        has_sub = self.subscriptions.has(subscriber)
        if not has_sub and hasattr(subscriber, "account"):
            # it's common to send an Object when we
            # by default only allow Accounts to subscribe.
            has_sub = self.subscriptions.has(subscriber.account)
        return has_sub

    @property
    def mutelist(self):
        return self.db.mute_list or []

    @property
    def banlist(self):
        return self.db.ban_list or []

    @property
    def wholist(self):
        subs = self.subscriptions.all()
        muted = list(self.mutelist)
        listening = [ob for ob in subs if ob.is_connected and ob not in muted]
        if subs:
            # display listening subscribers in bold
            string = ", ".join(
                [
                    account.key if account not in listening else "|w%s|n" % account.key
                    for account in subs
                ]
            )
        else:
            string = "<None>"
        return string

    def mute(self, subscriber, **kwargs):
        """
        Adds an entity to the list of muted subscribers.
        A muted subscriber will no longer see channel messages,
        but may use channel commands.

        Args:
            subscriber (Object or Account): Subscriber to mute.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            bool: True if muting was successful, False if we were already
                muted.

        """
        mutelist = self.mutelist
        if subscriber not in mutelist:
            mutelist.append(subscriber)
            self.db.mute_list = mutelist
            return True
        return False

    def unmute(self, subscriber, **kwargs):
        """
        Removes an entity from the list of muted subscribers.  A muted subscriber
        will no longer see channel messages, but may use channel commands.

        Args:
            subscriber (Object or Account): The subscriber to unmute.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            bool: True if unmuting was successful, False if we were already
                unmuted.

        """
        mutelist = self.mutelist
        if subscriber in mutelist:
            mutelist.remove(subscriber)
            return True
        return False

    def ban(self, target, **kwargs):
        """
        Ban a given user from connecting to the channel. This will not stop
        users already connected, so the user must be booted for this to take
        effect.

        Args:
            target (Object or Account): The entity to unmute. This need not
                be a subscriber.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            bool: True if banning was successful, False if target was already
                banned.
        """
        banlist = self.banlist
        if target not in banlist:
            banlist.append(target)
            self.db.ban_list = banlist
            return True
        return False

    def unban(self, target, **kwargs):
        """
        Un-Ban a given user. This will not reconnect them - they will still
        have to reconnect and set up aliases anew.

        Args:
            target (Object or Account): The entity to unmute. This need not
                be a subscriber.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            bool: True if unbanning was successful, False if target was not
                previously banned.
        """
        banlist = list(self.banlist)
        if target in banlist:
            banlist = [banned for banned in banlist if banned != target]
            self.db.ban_list = banlist
            return True
        return False

    def connect(self, subscriber, **kwargs):
        """
        Connect the user to this channel. This checks access.

        Args:
            subscriber (Account or Object): the entity to subscribe
                to this channel.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            success (bool): Whether or not the addition was
                successful.

        """
        # check access
        if subscriber in self.banlist or not self.access(subscriber, "listen"):
            return False
        # pre-join hook
        connect = self.pre_join_channel(subscriber)
        if not connect:
            return False
        # subscribe
        self.subscriptions.add(subscriber)
        # unmute
        self.unmute(subscriber)
        # post-join hook
        self.post_join_channel(subscriber)
        return True

    def disconnect(self, subscriber, **kwargs):
        """
        Disconnect entity from this channel.

        Args:
            subscriber (Account of Object): the
                entity to disconnect.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            success (bool): Whether or not the removal was
                successful.

        """
        # pre-disconnect hook
        disconnect = self.pre_leave_channel(subscriber)
        if not disconnect:
            return False
        # disconnect
        self.subscriptions.remove(subscriber)
        # unmute
        self.unmute(subscriber)
        # post-disconnect hook
        self.post_leave_channel(subscriber)
        return True

    def access(
        self,
        accessing_obj,
        access_type="listen",
        default=False,
        no_superuser_bypass=False,
        **kwargs,
    ):
        """
        Determines if another object has permission to access.

        Args:
            accessing_obj (Object): Object trying to access this one.
            access_type (str, optional): Type of access sought.
            default (bool, optional): What to return if no lock of access_type was found
            no_superuser_bypass (bool, optional): Turns off superuser
                lock bypass. Be careful with this one.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            return (bool): Result of lock check.

        """
        return self.locks.check(
            accessing_obj,
            access_type=access_type,
            default=default,
            no_superuser_bypass=no_superuser_bypass,
        )

    @classmethod
    def create(cls, key, creator=None, *args, **kwargs):
        """
        Creates a basic Channel with default parameters, unless otherwise
        specified or extended.

        Provides a friendlier interface to the utils.create_channel() function.

        Args:
            key (str): This must be unique.
            creator (Account or Object): Entity to associate with this channel
                (used for tracking)

        Keyword Args:
            aliases (list of str): List of alternative (likely shorter) keynames.
            description (str): A description of the channel, for use in listings.
            locks (str): Lockstring.
            keep_log (bool): Log channel throughput.
            typeclass (str or class): The typeclass of the Channel (not
                often used).
            ip (str): IP address of creator (for object auditing).

        Returns:
            channel (Channel): A newly created Channel.
            errors (list): A list of errors in string form, if any.

        """
        errors = []
        obj = None
        ip = kwargs.pop("ip", "")

        try:
            kwargs["desc"] = kwargs.pop("description", "")
            kwargs["typeclass"] = kwargs.get("typeclass", cls)
            obj = create.create_channel(key, *args, **kwargs)

            # Record creator id and creation IP
            if ip:
                obj.db.creator_ip = ip
            if creator:
                obj.db.creator_id = creator.id

        except Exception as exc:
            errors.append("An error occurred while creating this '%s' object." % key)
            logger.log_err(exc)

        return obj, errors

    def delete(self):
        """
        Deletes channel.

        Returns:
            bool: If deletion was successful. Only time it can fail would be
                if channel was already deleted. Even if it were to fail, all subscribers
                will be disconnected.

        """
        self.attributes.clear()
        self.aliases.clear()
        for subscriber in self.subscriptions.all():
            self.disconnect(subscriber)
        if not self.pk:
            return False
        super().delete()
        return True

    def channel_prefix(self):
        """
        Hook method. How the channel should prefix itself for users.

        Returns:
            str: The channel prefix.

        """
        return self.channel_prefix_string.format(channelname=self.key)

    def add_user_channel_alias(self, user, alias, **kwargs):
        """
        Add a personal user-alias for this channel to a given subscriber.

        Args:
            user (Object or Account): The one to alias this channel.
            alias (str): The desired alias.

        Note:
            This is tightly coupled to the default `channel` command. If you
            change that, you need to change this as well.

            We add two nicks - one is a plain `alias -> channel.key` that
            users need to be able to reference this channel easily. The other
            is a templated nick to easily be able to send messages to the
            channel without needing to give the full `channel` command. The
            structure of this nick is given by `self.channel_msg_nick_pattern`
            and `self.channel_msg_nick_replacement`. By default it maps
            `alias <msg> -> channel <channelname> = <msg>`, so that you can
            for example just write `pub Hello` to send a message.

            The alias created is `alias $1 -> channel channel = $1`, to allow
            for sending to channel using the main channel command.

        """
        chan_key = self.key.lower()

        # the message-pattern allows us to type the channel on its own without
        # needing to use the `channel` command explicitly.
        msg_nick_pattern = self.channel_msg_nick_pattern.format(alias=alias)
        msg_nick_replacement = self.channel_msg_nick_replacement.format(channelname=chan_key)
        user.nicks.add(
            msg_nick_pattern,
            msg_nick_replacement,
            category="inputline",
            pattern_is_regex=True,
            **kwargs,
        )

        if chan_key != alias:
            # this allows for using the alias for general channel lookups
            user.nicks.add(alias, chan_key, category="channel", **kwargs)

    @classmethod
    def remove_user_channel_alias(cls, user, alias, **kwargs):
        """
        Remove a personal channel alias from a user.

        Args:
           user (Object or Account): The user to remove an alias from.
           alias (str): The alias to remove.
           **kwargs: Unused by default. Can be used to pass extra variables
                into a custom implementation.

        Notes:
            The channel-alias actually consists of two aliases - one
            channel-based one for searching channels with the alias and one
            inputline one for doing the 'channelalias msg' - call.

            This is a classmethod because it doesn't actually operate on the
            channel instance.

            It sits on the channel because the nick structure for this is
            pretty complex and needs to be located in a central place (rather
            on, say, the channel command).

        """
        user.nicks.remove(alias, category="channel", **kwargs)
        msg_nick_pattern = cls.channel_msg_nick_pattern.format(alias=alias)
        user.nicks.remove(msg_nick_pattern, category="inputline", **kwargs)

    def at_pre_msg(self, message, **kwargs):
        """
        Called before the starting of sending the message to a receiver. This
        is called before any hooks on the receiver itself. If this returns
        None/False, the sending will be aborted.

        Args:
            message (str): The message to send.
            **kwargs (any): Keywords passed on from `.msg`. This includes
                `senders`.

        Returns:
            str, False or None: Any custom changes made to the message. If
                falsy, no message will be sent.

        """
        return message

    def msg(self, message, senders=None, bypass_mute=False, **kwargs):
        """
        Send message to channel, causing it to be distributed to all non-muted
        subscribed users of that channel.

        Args:
            message (str): The message to send.
            senders (Object, Account or list, optional): If not given, there is
                no way to associate one or more senders with the message (like
                a broadcast message or similar).
            bypass_mute (bool, optional): If set, always send, regardless of
                individual mute-state of subscriber. This can be used for
                global announcements or warnings/alerts.
            **kwargs (any): This will be passed on to all hooks. Use `no_prefix`
                to exclude the channel prefix.

        Notes:
            The call hook calling sequence is:

            - `msg = channel.at_pre_msg(message, **kwargs)` (aborts for all if return None)
            - `msg = receiver.at_pre_channel_msg(msg, channel, **kwargs)` (aborts for receiver if return None)
            - `receiver.at_channel_msg(msg, channel, **kwargs)`
            - `receiver.at_post_channel_msg(msg, channel, **kwargs)``
            Called after all receivers are processed:
            - `channel.at_post_all_msg(message, **kwargs)`

            (where the senders/bypass_mute are embedded into **kwargs for
            later access in hooks)

        """
        senders = make_iter(senders) if senders else []
        if self.send_to_online_only:
            receivers = self.subscriptions.online()
        else:
            receivers = self.subscriptions.all()
        if not bypass_mute:
            receivers = [receiver for receiver in receivers if receiver not in self.mutelist]

        send_kwargs = {"senders": senders, "bypass_mute": bypass_mute, **kwargs}

        # pre-send hook
        message = self.at_pre_msg(message, **send_kwargs)
        if message in (None, False):
            return

        for receiver in receivers:
            # send to each individual subscriber

            try:
                recv_message = receiver.at_pre_channel_msg(message, self, **send_kwargs)
                if recv_message in (None, False):
                    return

                receiver.channel_msg(recv_message, self, **send_kwargs)

                receiver.at_post_channel_msg(recv_message, self, **send_kwargs)

            except Exception:
                logger.log_trace(f"Error sending channel message to {receiver}.")

        # post-send hook
        self.at_post_msg(message, **send_kwargs)

    def at_post_msg(self, message, **kwargs):
        """
        This is called after sending to *all* valid recipients. It is normally
        used for logging/channel history.

        Args:
            message (str): The message sent.
            **kwargs (any): Keywords passed on from `msg`, including `senders`.

        """
        # save channel history to log file
        log_file = self.get_log_filename()
        if log_file:
            senders = ",".join(sender.key for sender in kwargs.get("senders", []))
            senders = f"{senders}: " if senders else ""
            message = f"{senders}{message}"
            logger.log_file(message, log_file)

    def pre_join_channel(self, joiner, **kwargs):
        """
        Hook method. Runs right before a channel is joined. If this
        returns a false value, channel joining is aborted.

        Args:
            joiner (object): The joining object.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            should_join (bool): If `False`, channel joining is aborted.

        """
        return True

    def post_join_channel(self, joiner, **kwargs):
        """
        Hook method. Runs right after an object or account joins a channel.

        Args:
            joiner (object): The joining object.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:
            By default this adds the needed channel nicks to the joiner.

        """
        key_and_aliases = [self.key.lower()] + [alias.lower() for alias in self.aliases.all()]
        for key_or_alias in key_and_aliases:
            self.add_user_channel_alias(joiner, key_or_alias, **kwargs)

    def pre_leave_channel(self, leaver, **kwargs):
        """
        Hook method. Runs right before a user leaves a channel. If this returns a false
        value, leaving the channel will be aborted.

        Args:
            leaver (object): The leaving object.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            should_leave (bool): If `False`, channel parting is aborted.

        """
        return True

    def post_leave_channel(self, leaver, **kwargs):
        """
        Hook method. Runs right after an object or account leaves a channel.

        Args:
            leaver (object): The leaving object.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        chan_key = self.key.lower()
        key_or_aliases = [self.key.lower()] + [alias.lower() for alias in self.aliases.all()]
        nicktuples = leaver.nicks.get(category="channel", return_tuple=True, return_list=True)
        key_or_aliases += [tup[2] for tup in nicktuples if tup[3].lower() == chan_key]
        for key_or_alias in key_or_aliases:
            self.remove_user_channel_alias(leaver, key_or_alias, **kwargs)

    def at_init(self):
        """
        Hook method. This is always called whenever this channel is
        initiated -- that is, whenever it its typeclass is cached from
        memory. This happens on-demand first time the channel is used
        or activated in some way after being created but also after
        each server restart or reload.

        """
        pass

    #
    # Web/Django methods
    #

    def web_get_admin_url(self):
        """
        Returns the URI path for the Django Admin page for this object.

        ex. Account#1 = '/admin/accounts/accountdb/1/change/'

        Returns:
            path (str): URI path to Django Admin page for object.

        """
        content_type = ContentType.objects.get_for_model(self.__class__)
        return reverse(
            "admin:%s_%s_change" % (content_type.app_label, content_type.model), args=(self.id,)
        )

    @classmethod
    def web_get_create_url(cls):
        """
        Returns the URI path for a View that allows users to create new
        instances of this object.

        ex. Chargen = '/characters/create/'

        For this to work, the developer must have defined a named view somewhere
        in urls.py that follows the format 'modelname-action', so in this case
        a named view of 'channel-create' would be referenced by this method.

        ex.
        url(r'channels/create/', ChannelCreateView.as_view(), name='channel-create')

        If no View has been created and defined in urls.py, returns an
        HTML anchor.

        This method is naive and simply returns a path. Securing access to
        the actual view and limiting who can create new objects is the
        developer's responsibility.

        Returns:
            path (str): URI path to object creation page, if defined.

        """
        try:
            return reverse("%s-create" % slugify(cls._meta.verbose_name))
        except Exception:
            return "#"

    def web_get_detail_url(self):
        """
        Returns the URI path for a View that allows users to view details for
        this object.

        ex. Oscar (Character) = '/characters/oscar/1/'

        For this to work, the developer must have defined a named view somewhere
        in urls.py that follows the format 'modelname-action', so in this case
        a named view of 'channel-detail' would be referenced by this method.

        ex.
        ::

            url(r'channels/(?P<slug>[\w\d\-]+)/$',
                ChannelDetailView.as_view(), name='channel-detail')

        If no View has been created and defined in urls.py, returns an
        HTML anchor.

        This method is naive and simply returns a path. Securing access to
        the actual view and limiting who can view this object is the developer's
        responsibility.

        Returns:
            path (str): URI path to object detail page, if defined.

        """
        try:
            return reverse(
                "%s-detail" % slugify(self._meta.verbose_name),
                kwargs={"slug": slugify(self.db_key)},
            )
        except Exception:
            return "#"

    def web_get_update_url(self):
        """
        Returns the URI path for a View that allows users to update this
        object.

        ex. Oscar (Character) = '/characters/oscar/1/change/'

        For this to work, the developer must have defined a named view somewhere
        in urls.py that follows the format 'modelname-action', so in this case
        a named view of 'channel-update' would be referenced by this method.

        ex.
        ::

            url(r'channels/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/change/$',
                ChannelUpdateView.as_view(), name='channel-update')

        If no View has been created and defined in urls.py, returns an
        HTML anchor.

        This method is naive and simply returns a path. Securing access to
        the actual view and limiting who can modify objects is the developer's
        responsibility.

        Returns:
            path (str): URI path to object update page, if defined.

        """
        try:
            return reverse(
                "%s-update" % slugify(self._meta.verbose_name),
                kwargs={"slug": slugify(self.db_key)},
            )
        except Exception:
            return "#"

    def web_get_delete_url(self):
        """
        Returns the URI path for a View that allows users to delete this object.

        ex. Oscar (Character) = '/characters/oscar/1/delete/'

        For this to work, the developer must have defined a named view somewhere
        in urls.py that follows the format 'modelname-action', so in this case
        a named view of 'channel-delete' would be referenced by this method.

        ex.
        url(r'channels/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/delete/$',
            ChannelDeleteView.as_view(), name='channel-delete')

        If no View has been created and defined in urls.py, returns an
        HTML anchor.

        This method is naive and simply returns a path. Securing access to
        the actual view and limiting who can delete this object is the developer's
        responsibility.

        Returns:
            path (str): URI path to object deletion page, if defined.

        """
        try:
            return reverse(
                "%s-delete" % slugify(self._meta.verbose_name),
                kwargs={"slug": slugify(self.db_key)},
            )
        except Exception:
            return "#"

    # Used by Django Sites/Admin
    get_absolute_url = web_get_detail_url

    # TODO Evennia 1.0+ removed hooks. Remove in 1.1.
    def message_transform(self, *args, **kwargs):
        raise RuntimeError(
            "Channel.message_transform is no longer used in 1.0+. "
            "Use Account/Object.at_pre_channel_msg instead."
        )

    def distribute_message(self, msgobj, online=False, **kwargs):
        raise RuntimeError("Channel.distribute_message is no longer used in 1.0+.")

    def format_senders(self, senders=None, **kwargs):
        raise RuntimeError(
            "Channel.format_senders is no longer used in 1.0+. "
            "Use Account/Object.at_pre_channel_msg instead."
        )

    def pose_transform(self, msgobj, sender_string, **kwargs):
        raise RuntimeError(
            "Channel.pose_transform is no longer used in 1.0+. "
            "Use Account/Object.at_pre_channel_msg instead."
        )

    def format_external(self, msgobj, senders, emit=False, **kwargs):
        raise RuntimeError(
            "Channel.format_external is no longer used in 1.0+. "
            "Use Account/Object.at_pre_channel_msg instead."
        )

    def format_message(self, msgobj, emit=False, **kwargs):
        raise RuntimeError(
            "Channel.format_message is no longer used in 1.0+. "
            "Use Account/Object.at_pre_channel_msg instead."
        )

    def pre_send_message(self, msg, **kwargs):
        raise RuntimeError("Channel.pre_send_message was renamed to Channel.at_pre_msg.")

    def post_send_message(self, msg, **kwargs):
        raise RuntimeError("Channel.post_send_message was renamed to Channel.at_post_msg.")
