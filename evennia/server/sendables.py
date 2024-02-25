from evennia.utils.utils import classproperty
from evennia.utils.ansi import ANSIString, parse_ansi, AnsiToHtmlConverter


RG = AnsiToHtmlConverter()


class Sendable:
    """
    Abstract base class used for Evennia's built-in sendables. This class CAN be used, but it does nothing. Its primary
    purpose is specifying the basic interface for Sendables.

    Multiple PortalSessions can receive the same Sendable instance. Take care when coding rendering, exporting methods,
    etc, so that all PortalSessions can use it properly.

    Sendables are loaded from modules specified in settings.py and indexed using their sendable_name class property.
    This allows them to be sub-classed and replaced with custom versions with replaced or enhanced behaviors and
    more features.

    They are instantiated on the Server to represent outgoing messages and activity. They are sent by using the .send()
    method on a ServerSession, Account, or Object, which distributes them to one or more PortalSessions.

    Thus, Sendables must be able to be pickled, which means that they should contain anything that wouldn't be found
    in JSON data. Pickle can handle many things, but it is vulnerable to issues like circular references or objects that
    are linked to the database.

    Because they can be serialized into JSON or stable pickleable data, Sendables can be logged, archived, serialized in
    a number of ways and used to reconstruct messages again later. This is useful for things like direct message
    history, messages received in a room while offline being logged, etc.

    Class Properties:
        sendable_name (str): The name of the sendable. Defaults to the class name in lowercase.
    """

    @classproperty
    def sendable_name(cls) -> str:
        return cls.__name__.lower()

    def get_render_types(self, session, metadata) -> tuple[str, ...]:
        """
        Generates a tuple of strings representing the render types the sendable can be rendered as.
        Normal types are "oob", "ansi", "html", and "json", but it's easy to add more.

        In most cases this is fixed for the class, but it can be dynamic if needed.

        For instance, it may be useful to have a sendable that can be rendered as "html" or "ansi" depending on
        whether the PortalSession is a web client or a telnet client. Or, a table or chat message sent using GMCP
        might fall back to ansi if the client doesn't support GMCP.

        Args:
            session (PortalSession): The session that received the sendable.
            metadata (dict): Metadata about the whole message.

        Returns:
            tuple[str, ...]: The render types the sendable can be rendered as.
        """
        return tuple()

    def at_portal_session_receive(self, session, metadata):
        """
        This method is called when the sendable is received by the portal session.
        Since it has direct access to the session, it can do pretty much anything.
        You can use it to set variables, change options, etc.

        Args:
            session (PortalSession): The session that received the sendable.
            metadata (dict): Metadata about the whole message.
        """
        pass

    def render_as_ansi(self, session, metadata) -> str:
        """
        This method is called when the sendable is being rendered as ANSI.

        Args:
            session (PortalSession): The session that received the sendable.
            metadata (dict): Metadata about the whole message.

        Returns:
            str: The rendered sendable.
        """
        return ""

    def render_as_html(self, session, metadata) -> str:
        """
        This method is called when the sendable is being rendered as HTML.

        Args:
            session (PortalSession): The session that received the sendable.
            metadata (dict): Metadata about the whole message.

        Returns:
            str: The rendered sendable.
        """
        return ""

    def render_as_json(self, session, metadata) -> list | dict | int | float | None | str:
        """
        This method is called when the sendable is being rendered as JSON.

        Args:
            session (PortalSession): The session that received the sendable.
            metadata (dict): Metadata about the whole message.

        Returns:
            (list | dict | int | float | None | str): The rendered sendable.
                This should be primitives that can be json.dumps'd.
        """
        return ""

    def render_as_oob(self, session, metadata) -> [str, list, dict]:
        """
        This method is called when the sendable is being rendered as OOB. Primarily used for legacy messagepath
        compatability.

        Args:
            session (PortalSession): The session that received the sendable.
            metadata (dict): Metadata about the whole message.

        Returns:
            [str, list, dict]: The rendered sendable.
                This should be primitives that can be json.dumps'd.
        """
        return [self.__class__.sendable_name, list(), dict()]

    def serialize_sendable(self) -> (str, "Any"):
        """
        Used to serialize the Sendable into a tuple that can be used to reconstruct it later.

        The first item in the tuple is simply used to identify the sendable by sendable_name.
        The second item will be passed to the relevant Sendable.deserialize_sendable() method.

        Returns:
            (str, Any): A tuple containing the class name and the data needed to reconstruct the Sendable. The
                'Any' data should be JSONable primitives like dictionaries, strings, numbers, etc.
        """
        return (
            self.__class__.sendable_name,
            self.serialize_sendable_data(),
        )

    def serialize_sendable_data(self):
        """
        Helper method used to serialize the Sendable's data into a tuple, dictionary, or similar primitive that
        can be used to reconstruct it later.

        Returns:
            Any: JSONable primitive data.
        """
        return None

    @classmethod
    def deserialize_sendable(cls, data):
        """
        Used to reconstruct the Sendable from a tuple. Must be given the second element from the tuple generated
        by Sendable.serialize_sendable().

        Args:
            data (Any): The data needed to reconstruct the Sendable.

        Returns:
            Sendable: The reconstructed Sendable.
        """
        raise NotImplementedError()


class EvString(Sendable):
    """
    A sendable that represents a string. This is the most basic sendable.

    This isn't the real EvString, just a placeholder for testing while
    Inspector Caracal works on the real deal.
    """

    sendable_name = "text"

    def get_render_types(self, session, metadata) -> tuple[str, ...]:
        return "oob", "html", "json"

    def __init__(self, string, **kwargs):
        self.original = string
        self.string = string
        self.kwargs = kwargs

    def render_as_ansi(self, session, metadata) -> str:
        return parse_ansi(self.string)

    def render_as_html(self, session, metadata) -> str:
        return RG.convert(parse_ansi(self.string))

    def render_as_json(self, session, metadata) -> str:
        return RG.convert(parse_ansi(self.string))

    def render_as_oob(self, session, metadata) -> [str, list, dict]:
        return ["text", [parse_ansi(self.string)], self.kwargs]

    def serialize_sendable_data(self):
        return self.original, self.kwargs

    @classmethod
    def deserialize_sendable(cls, data):
        return cls(data[0], **data[1])


class OOBFunc(Sendable):
    """
    Basic class for sending OOB-commands that aren't 'text' using the legacy Evennia msgpath.

    For telnet clients this will be coerced to MSDP and possibly then sent over GMCP as long as protocol_flags["OOB"] is True.
    """

    sendable_name = "oob"

    def get_render_types(self, session, metadata) -> tuple[str, ...]:
        return "oob", "json"

    def __init__(self, cmd: str, *args, **kwargs):
        """
        It is absolutely imperative that input can be coerced into the format of:
        [cmdname, [*args], {**kwargs}]

        Like...
        ["map", ["mapname"], {"x": 1, "y": 2}]

        It's sent as effectively JSON. everything must be primitives like strings, numbers, lists, etc.

        Args:
            cmd (str): The name of the command to call.
            *args (list): The arguments to pass to the command.
            **kwargs (dict): The keyword arguments to pass to the command.
        """
        self.cmd = cmd
        self.args = args
        self.kwargs = kwargs

    def render_as_oob(self, session, metadata) -> [str, list, dict]:
        return [self.cmd, self.args, self.kwargs]

    def render_as_json(self, session, metadata) -> [str, list, dict]:
        return ["oob", self.cmd, self.args, self.kwargs]

    def serialize_sendable_data(self):
        return self.cmd, self.args, self.kwargs

    @classmethod
    def deserialize_sendable(cls, data):
        return cls(data[0], *data[1], **data[2])


class GMCP(Sendable):
    """
    The GMCP type is used to send GMCP data to the client. For Telnets, this requires the actual GMCP protocol to be
    enabled in protocol_flags["GMCP"]. For web clients, this will be sent as JSON.
    """

    def __init__(self, cmd: str, data: dict = None):
        """
        Args:
            cmd (str): The GMCP command to send.
            data (dict, optional): The data to send. Defaults to None.
        """
        self.cmd = cmd
        self.data = data

    def get_render_types(self, session, metadata) -> tuple[str, ...]:
        return "gmcp", "json"

    def render_as_gmcp(self, session, metadata) -> tuple[str, "Any"]:
        """
        Returns the GMCP command and data as a tuple.

        Args:
            session (PortalSession): The session that received the sendable.
            metadata (dict): Metadata about the whole message.

        Returns:
            tuple[str, Any]: The GMCP command and data. The Any data should be JSONable primitives like dictionaries,
                strings, numbers, etc. If the data is None, it will be omitted and sent as a naked command.
        """
        return self.cmd, self.data

    def render_as_json(self, session, metadata) -> tuple[str, str, "Any"]:
        """
        Returns the GMCP command and data as a tuple.

        Args:
            session (PortalSession): The session that received the sendable.
            metadata (dict): Metadata about the whole message.

        Returns:
            tuple[str, str, Any]: The GMCP command and data. The Any data should be JSONable primitives like
                dictionaries, strings, numbers, etc. If the data is None, it will be omitted and sent as a naked
                command.
        """
        return "gmcp", self.cmd, self.data

    def serialize_sendable_data(self):
        return self.cmd, self.data

    @classmethod
    def deserialize_sendable(cls, data):
        return cls(data[0], data[1])


class ReprHandler(Sendable):
    """
    The ReprHandler type is used to send a repr() of an object to the client. This allows for syntax highlighting and
    similar special treatment of the data. This is mainly used by the @py command.

    The base Evennia variant doesn't do anything special with this, but it can be overloaded and replaced easily.
    """

    sendable_name = "repr"

    def get_render_types(self, session, metadata) -> tuple[str, ...]:
        return ("ansi",)

    def __init__(self, data, **kwargs):
        """
        Construct a ReprHandler.

        Args:
            data (str): The output from repr() which is to be rendered.
        """
        self.data = data
        self.kwargs = kwargs

    def render_as_ansi(self, session, metadata) -> str:
        """
        Returns the data as a string.

        Args:
            session (PortalSession): The session that received the sendable.
            metadata (dict): Metadata about the whole message.

        Returns:
            str: The data as a string.
        """
        print(f"PRINTING REPR: {self.data}")
        if prefix := self.kwargs.get("prefix", ""):
            return f"{prefix} {self.data}"
        return self.data

    def serialize_sendable_data(self):
        return self.data, self.kwargs

    @classmethod
    def deserialize_sendable(cls, data):
        return cls(data[0], **data[1])
