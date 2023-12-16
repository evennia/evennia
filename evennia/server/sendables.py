from evennia.utils.ansi import ANSIString, parse_ansi, AnsiToHtmlConverter

RG = AnsiToHtmlConverter()


class Sendable:
    """
    Abstract base class used for Evennia's built-in sendables. This class CAN be used, but it does nothing.

    Multiple PortalSessions may receive the same Sendable instance, so be careful about modifying a Sendable's
    state.
    """

    # A set of strings representing the render types the sendable can be rendered as.
    # Normal types are "oob", "ansi", "html", and "json", but it's easy to add more.
    render_types = ()

    def at_portal_session_receive(self, session, metadata):
        """
        This method is called when the sendable is received by the portal session.
        Since it has direct access to the session, it can do pretty much anything.
        You can use it to set variables, change options, etc. Just be careful.

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
        This method is called when the sendable is being rendered as OOB.

        Args:
            session (PortalSession): The session that received the sendable.
            metadata (dict): Metadata about the whole message.

        Returns:
            [str, list, dict]: The rendered sendable.
                This should be primitives that can be json.dumps'd.
        """
        return [getattr(self, "sendable_name", self.__class__.__name__.lower()), list(), dict()]

    def serialize_sendable(self) -> (str, "Any"):
        """
        Used to serialize the Sendable into a tuple that can be used to reconstruct it later.

        Returns:
            (str, Any): A tuple containing the class name and the data needed to reconstruct the Sendable.
        """
        return (
            getattr(self, "sendable_name", self.__class__.__name__),
            self.serialize_sendable_data(),
        )

    def serialize_sendable_data(self):
        return None

    @classmethod
    def deserialize_sendable(cls, data):
        """
        Used to reconstruct the Sendable from a tuple.

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

    render_types = ("oob",)

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


class OOBFunc(Sendable):
    """
    Basic class for sending OOB-commands that aren't 'text' using the legacy Evennia msgpath.
    """

    sendable_name = "oob"

    render_types = ("oob",)

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
