from collections import defaultdict
from django.conf import settings
from evennia.utils.utils import class_from_module, lazy_property
from evennia.utils.optionhandler import OptionHandler
from evennia.utils.logger import log_trace

_BASE_SESSION_CLASS = class_from_module(settings.BASE_SESSION_CLASS)


class PortalSession(_BASE_SESSION_CLASS):
    def supports_render_type(self, render_type: str) -> bool:
        """
        Returns whether or not this session supports a given render type.

        Args:
            render_type (str): The render type to check.

        Returns:
            bool: Whether or not the session supports the render type.
        """
        return False

    @lazy_property
    def session_options(self):
        """
        Just as with the Server-side Account typeclass, PortalSessions have an OptionHandler. It replicates
        options available on the Account and receives changes from the Account when they occur.

        NOTE: Because Twisted's Telnet Protocol also has an .options, this is .session_options.
        """
        return OptionHandler(
            self,
            options_dict=settings.OPTIONS_ACCOUNT_DEFAULT,
            save_kwargs={"category": "option"},
            load_kwargs={"category": "option"},
        )

    def sendables_out(self, sendables: list["Any"], metadata: dict, **kwargs):
        """
        Called by the PortalSessionHandler when it's time to send sendables to the client.

        Args:
            sendables (list[Sendable]): The sendables to send.
            metadata (dict): Metadata about the whole message. Might be empty.
            **kwargs: Any additional keyword arguments. Not used by default.
        """
        if not sendables:
            return

        # call session hooks, if available. (they SHOULD be available, but some custom Sendables
        # might not have them.)
        for sendable in sendables:
            if callable(hook := getattr(sendable, "at_portal_session_receive", None)):
                hook(self, metadata)

        # filter sendables by render type.
        filtered_sendables = self.filter_sendables(sendables, metadata)
        if not filtered_sendables:
            return

        for rt, filtered in filtered_sendables.items():
            if callable(method := getattr(self, f"handle_sendables_{rt}", None)):
                method(filtered, metadata)

        # Finally, call the at_after_sendables hook.
        self.at_post_sendables_out(sendables, metadata)

    def at_post_sendables_out(self, sendables: list["Any"], metadata: dict, **kwargs):
        """
        This is called after sendables are processed. use it for any cleanups or other processing.

        Args:
            sendables (list[Sendable]): The sendables that were sent.
            metadata (dict): Metadata about the whole message. Might be empty.
            **kwargs: Any additional keyword arguments. Not used by default.
        """
        pass

    def filter_sendables(self, sendables: list["Any"], metadata: dict) -> dict[str, list["Any"]]:
        """
        Helper method for filtering sendables by render type.

        Sendables are filtered by whether they produce a render_type that the session supports.
        Via the get_render_types method, sendables are allowed to be choosy about what render types
        they want to use. This means one could decide it wants to prioritize a render_type over another,
        if the session supports both.

        Args:
            sendables (list[Sendable]): The sendables to filter.

        Returns:
            dict[str, list[Sendable]]: A dictionary of sendables, keyed by render type.
        """
        out = defaultdict(list)
        for sendable in sendables:
            for render_type in sendable.get_render_types(self, metadata):
                if self.supports_render_type(render_type):
                    out[render_type].append(sendable)
        return out

    def handle_sendables_oob(self, sendables: list, metadata: dict):
        """
        Called by sendables_out to handle OOB sendables.

        Args:
            sendables (list[Sendable]): The sendables to send.
            metadata (dict): Metadata about the whole message. Might be empty.
        """
        options = metadata.get("options", dict())
        for sendable in sendables:
            if callable(method := getattr(sendable, "render_as_oob", None)):
                try:
                    cmd, args, kw = method(self, metadata)
                    kw["options"] = options
                    if callable(send_func := getattr(self, f"send_{cmd.strip().lower()}", None)):
                        send_func(*args, **kw)
                    else:
                        self.send_default(cmd, *args, **kw)
                except Exception:
                    log_trace()

    def handle_sendables_ansi(self, sendables: list, metadata: dict):
        """
        Called by sendables_out to handle text sendables.

        Args:
            sendables (list[Sendable]): The sendables to send.
            metadata (dict): Metadata about the whole message. Might be empty.
        """
        options = metadata.get("options", dict())
        for sendable in sendables:
            if callable(method := getattr(sendable, "render_as_ansi", None)):
                try:
                    text = method(self, metadata)
                    self.send_text(*[text], **options)
                except Exception:
                    log_trace()
