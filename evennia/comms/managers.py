"""
These managers define helper methods for accessing the database from
Comm system components.

"""


from django.conf import settings
from django.db.models import Q

from evennia.server import signals
from evennia.typeclasses.managers import TypeclassManager, TypedObjectManager
from evennia.utils import logger
from evennia.utils.utils import class_from_module, dbref, make_iter

_GA = object.__getattribute__
_AccountDB = None
_ObjectDB = None
_ChannelDB = None
_ScriptDB = None
_SESSIONS = None

# error class


class CommError(Exception):
    """
    Raised by comm system, to allow feedback to player when caught.
    """

    pass


#
# helper functions
#


def identify_object(inp):
    """
    Helper function. Identifies if an object is an account or an object;
    return its database model

    Args:
        inp (any): Entity to be idtified.

    Returns:
        identified (tuple): This is a tuple with (`inp`, identifier)
            where `identifier` is one of "account", "object", "channel",
            "string", "dbref" or None.

    """
    if hasattr(inp, "__dbclass__"):
        clsname = inp.__dbclass__.__name__
        if clsname == "AccountDB":
            return inp, "account"
        elif clsname == "ObjectDB":
            return inp, "object"
        elif clsname == "ChannelDB":
            return inp, "channel"
        elif clsname == "ScriptDB":
            return inp, "script"
    if isinstance(inp, str):
        return inp, "string"
    elif dbref(inp):
        return dbref(inp), "dbref"
    else:
        return inp, None


def to_object(inp, objtype="account"):
    """
    Locates the object related to the given accountname or channel key.
    If input was already the correct object, return it.

    Args:
        inp (any): The input object/string
        objtype (str): Either 'account' or 'channel'.

    Returns:
        obj (object): The correct object related to `inp`.

    """
    obj, typ = identify_object(inp)
    if typ == objtype:
        return obj
    if objtype == "account":
        if typ == "object":
            return obj.account
        if typ == "string":
            return _AccountDB.objects.get(user_username__iexact=obj)
        if typ == "dbref":
            return _AccountDB.objects.get(id=obj)
        logger.log_err("%s %s %s %s %s" % (objtype, inp, obj, typ, type(inp)))
        raise CommError()
    elif objtype == "object":
        if typ == "account":
            return obj.obj
        if typ == "string":
            return _ObjectDB.objects.get(db_key__iexact=obj)
        if typ == "dbref":
            return _ObjectDB.objects.get(id=obj)
        logger.log_err("%s %s %s %s %s" % (objtype, inp, obj, typ, type(inp)))
        raise CommError()
    elif objtype == "channel":
        if typ == "string":
            return _ChannelDB.objects.get(db_key__iexact=obj)
        if typ == "dbref":
            return _ChannelDB.objects.get(id=obj)
        logger.log_err("%s %s %s %s %s" % (objtype, inp, obj, typ, type(inp)))
        raise CommError()
    elif objtype == "script":
        if typ == "string":
            return _ScriptDB.objects.get(db_key__iexact=obj)
        if typ == "dbref":
            return _ScriptDB.objects.get(id=obj)
        logger.log_err("%s %s %s %s %s" % (objtype, inp, obj, typ, type(inp)))
        raise CommError()

    # an unknown
    return None


#
# Msg manager
#


class MsgManager(TypedObjectManager):
    """
    This MsgManager implements methods for searching and manipulating
    Messages directly from the database.

    These methods will all return database objects (or QuerySets)
    directly.

    A Message represents one unit of communication, be it over a
    Channel or via some form of in-game mail system. Like an e-mail,
    it always has a sender and can have any number of receivers (some
    of which may be Channels).

    """

    def identify_object(self, inp):
        """
        Wrapper to identify_object if accessing via the manager directly.

        Args:
            inp (any): Entity to be idtified.

        Returns:
            identified (tuple): This is a tuple with (`inp`, identifier)
                where `identifier` is one of "account", "object", "channel",
                "string", "dbref" or None.

        """
        return identify_object(inp)

    def get_message_by_id(self, idnum):
        """
        Retrieve message by its id.

        Args:
            idnum (int or str): The dbref to retrieve.

        Returns:
            message (Msg): The message.

        """
        try:
            return self.get(id=self.dbref(idnum, reqhash=False))
        except Exception:
            return None

    def get_messages_by_sender(self, sender):
        """
        Get all messages sent by one entity - this could be either a
        account or an object

        Args:
            sender (Account or Object): The sender of the message.

        Returns:
            QuerySet: Matching messages.

        Raises:
            CommError: For incorrect sender types.

        """
        obj, typ = identify_object(sender)
        if typ == "account":
            return self.filter(db_sender_accounts=obj).exclude(db_hide_from_accounts=obj)
        elif typ == "object":
            return self.filter(db_sender_objects=obj).exclude(db_hide_from_objects=obj)
        elif typ == "script":
            return self.filter(db_sender_scripts=obj)
        else:
            raise CommError

    def get_messages_by_receiver(self, recipient):
        """
        Get all messages sent to one given recipient.

        Args:
            recipient (Object, Account or Channel): The recipient of the messages to search for.

        Returns:
            Queryset: Matching messages.

        Raises:
            CommError: If the `recipient` is not of a valid type.

        """
        obj, typ = identify_object(recipient)
        if typ == "account":
            return self.filter(db_receivers_accounts=obj).exclude(db_hide_from_accounts=obj)
        elif typ == "object":
            return self.filter(db_receivers_objects=obj).exclude(db_hide_from_objects=obj)
        elif typ == "script":
            return self.filter(db_receivers_scripts=obj)
        else:
            raise CommError

    def search_message(self, sender=None, receiver=None, freetext=None, dbref=None):
        """
        Search the message database for particular messages. At least
        one of the arguments must be given to do a search.

        Args:
            sender (Object, Account or Script, optional): Get messages sent by a particular sender.
            receiver (Object, Account or Channel, optional): Get messages
                received by a certain account,object or channel
            freetext (str): Search for a text string in a message.  NOTE:
                This can potentially be slow, so make sure to supply one of
                the other arguments to limit the search.
            dbref (int): The exact database id of the message. This will override
                    all other search criteria since it's unique and
                    always gives only one match.

        Returns:
            Queryset: Iterable with 0, 1 or more matches.

        """
        # unique msg id
        if dbref:
            return self.objects.filter(id=dbref)

        # We use Q objects to gradually build up the query - this way we only
        # need to do one database lookup at the end rather than gradually
        # refining with multiple filter:s. Django Note: Q objects can be
        # combined with & and | (=AND,OR). ~ negates the queryset

        # filter by sender (we need __pk to avoid an error with empty Q() objects)
        sender, styp = identify_object(sender)
        if sender:
            spk = sender.pk
        if styp == "account":
            sender_restrict = Q(db_sender_accounts__pk=spk) & ~Q(db_hide_from_accounts__pk=spk)
        elif styp == "object":
            sender_restrict = Q(db_sender_objects__pk=spk) & ~Q(db_hide_from_objects__pk=spk)
        elif styp == "script":
            sender_restrict = Q(db_sender_scripts__pk=spk)
        else:
            sender_restrict = Q()
        # filter by receiver
        receiver, rtyp = identify_object(receiver)
        if receiver:
            rpk = receiver.pk
        if rtyp == "account":
            receiver_restrict = Q(db_receivers_accounts__pk=rpk) & ~Q(db_hide_from_accounts__pk=rpk)
        elif rtyp == "object":
            receiver_restrict = Q(db_receivers_objects__pk=rpk) & ~Q(db_hide_from_objects__pk=rpk)
        elif rtyp == "script":
            receiver_restrict = Q(db_receivers_scripts__pk=rpk)
        elif rtyp == "channel":
            raise DeprecationWarning(
                "Msg.objects.search don't accept channel recipients since "
                "Channels no longer accepts Msg objects."
            )
        else:
            receiver_restrict = Q()
        # filter by full text
        if freetext:
            fulltext_restrict = Q(db_header__icontains=freetext) | Q(db_message__icontains=freetext)
        else:
            fulltext_restrict = Q()
        # execute the query
        return self.filter(sender_restrict & receiver_restrict & fulltext_restrict)

    # back-compatibility alias
    message_search = search_message

    def create_message(
        self, senderobj, message, receivers=None, locks=None, tags=None, header=None, **kwargs
    ):
        """
        Create a new communication Msg. Msgs represent a unit of
        database-persistent communication between entites.

        Args:
            senderobj (Object, Account, Script, str or list): The entity (or
                entities) sending the Msg. If a `str`, this is the id-string
                for an external sender type.
            message (str): Text with the message. Eventual headers, titles
                etc should all be included in this text string. Formatting
                will be retained.
            receivers (Object, Account, Script, str or list): An Account/Object to send
                to, or a list of them. If a string, it's an identifier for an external
                receiver.
            locks (str): Lock definition string.
            tags (list): A list of tags or tuples `(tag, category)`.
            header (str): Mime-type or other optional information for the message

        Notes:
            The Comm system is created to be very open-ended, so it's fully
            possible to let a message both go several receivers at the same time,
            it's up to the command definitions to limit this as desired.

        """
        if "channels" in kwargs:
            raise DeprecationWarning(
                "create_message() does not accept 'channel' kwarg anymore "
                "- channels no longer accept Msg objects."
            )

        if not message:
            # we don't allow empty messages.
            return None
        new_message = self.model(db_message=message)
        new_message.save()
        for sender in make_iter(senderobj):
            new_message.senders = sender
        new_message.header = header
        for receiver in make_iter(receivers):
            new_message.receivers = receiver
        if locks:
            new_message.locks.add(locks)
        if tags:
            new_message.tags.batch_add(*tags)

        new_message.save()
        return new_message


#
# Channel manager
#


class ChannelDBManager(TypedObjectManager):
    """
    This ChannelManager implements methods for searching and
    manipulating Channels directly from the database.

    These methods will all return database objects (or QuerySets)
    directly.

    A Channel is an in-game venue for communication. It's essentially
    representation of a re-sender: Users sends Messages to the
    Channel, and the Channel re-sends those messages to all users
    subscribed to the Channel.

    """

    def get_all_channels(self):
        """
        Get all channels.

        Returns:
            channels (list): All channels in game.

        """
        return self.all()

    def get_channel(self, channelkey):
        """
        Return the channel object if given its key.
        Also searches its aliases.

        Args:
            channelkey (str): Channel key to search for.

        Returns:
            channel (Channel or None): A channel match.

        """
        dbref = self.dbref(channelkey)
        if dbref:
            try:
                return self.get(id=dbref)
            except self.model.DoesNotExist:
                pass
        results = self.filter(
            Q(db_key__iexact=channelkey)
            | Q(db_tags__db_tagtype__iexact="alias", db_tags__db_key__iexact=channelkey)
        ).distinct()
        return results[0] if results else None

    def get_subscriptions(self, subscriber):
        """
        Return all channels a given entity is subscribed to.

        Args:
            subscriber (Object or Account): The one subscribing.

        Returns:
            subscriptions (list): Channel subscribed to.

        """
        clsname = subscriber.__dbclass__.__name__
        if clsname == "AccountDB":
            return subscriber.account_subscription_set.all()
        if clsname == "ObjectDB":
            return subscriber.object_subscription_set.all()
        return []

    def search_channel(self, ostring, exact=True):
        """
        Search the channel database for a particular channel.

        Args:
            ostring (str): The key or database id of the channel.
            exact (bool, optional): Require an exact (but not
                case sensitive) match.

        Returns:
            Queryset: Iterable with 0, 1 or more matches.

        """
        dbref = self.dbref(ostring)
        if dbref:
            dbref_match = self.search_dbref(dbref)
            if dbref_match:
                return dbref_match

        if exact:
            channels = self.filter(
                Q(db_key__iexact=ostring)
                | Q(db_tags__db_tagtype__iexact="alias", db_tags__db_key__iexact=ostring)
            ).distinct()
        else:
            channels = self.filter(
                Q(db_key__icontains=ostring)
                | Q(db_tags__db_tagtype__iexact="alias", db_tags__db_key__icontains=ostring)
            ).distinct()
        return channels

    def create_channel(
        self, key, aliases=None, desc=None, locks=None, keep_log=True, typeclass=None, tags=None
    ):
        """
        Create A communication Channel. A Channel serves as a central hub
        for distributing Msgs to groups of people without specifying the
        receivers explicitly. Instead accounts may 'connect' to the channel
        and follow the flow of messages. By default the channel allows
        access to all old messages, but this can be turned off with the
        keep_log switch.

        Args:
            key (str): This must be unique.

        Keyword Args:
            aliases (list of str): List of alternative (likely shorter) keynames.
            desc (str): A description of the channel, for use in listings.
            locks (str): Lockstring.
            keep_log (bool): Log channel throughput.
            typeclass (str or class): The typeclass of the Channel (not
                often used).
            tags (list): A list of tags or tuples `(tag, category)`.

        Returns:
            channel (Channel): A newly created channel.

        """
        typeclass = typeclass if typeclass else settings.BASE_CHANNEL_TYPECLASS

        if isinstance(typeclass, str):
            # a path is given. Load the actual typeclass
            typeclass = class_from_module(typeclass, settings.TYPECLASS_PATHS)

        # create new instance
        new_channel = typeclass(db_key=key)

        # store call signature for the signal
        new_channel._createdict = dict(
            key=key, aliases=aliases, desc=desc, locks=locks, keep_log=keep_log, tags=tags
        )

        # this will trigger the save signal which in turn calls the
        # at_first_save hook on the typeclass, where the _createdict can be
        # used.
        new_channel.save()

        signals.SIGNAL_CHANNEL_POST_CREATE.send(sender=new_channel)

        return new_channel

    # back-compatibility alias
    channel_search = search_channel


class ChannelManager(ChannelDBManager, TypeclassManager):
    """
    Wrapper to group the typeclass manager to a consistent name.
    """

    pass
