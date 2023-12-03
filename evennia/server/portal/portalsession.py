from collections import defaultdict
from django.conf import settings
from evennia.utils.utils import class_from_module, lazy_property
from evennia.utils.optionhandler import OptionHandler
from evennia.utils.logger import log_trace

_BASE_SESSION_CLASS = class_from_module(settings.BASE_SESSION_CLASS)


class PortalSession(_BASE_SESSION_CLASS):
    render_types = ("oob", "ansi", "html", "json")

    @lazy_property
    def ev_options(self):
        """
        This ought to be .options, but it can't be due to how twisted's Telnet protocol works.
        """
        return OptionHandler(
            self,
            options_dict=settings.OPTIONS_ACCOUNT_DEFAULT,
            save_kwargs={"category": "option"},
            load_kwargs={"category": "option"},
        )

    def sendables_out(self, sendables: list["Any"], metadata: dict):
        if not sendables:
            return

        # call session hooks, if available. (they SHOULD be available, but some custom Sendables
        # might not have them.)
        for sendable in sendables:
            if callable(hook := getattr(sendable, "at_portal_session_receive", None)):
                hook(self, metadata)

        filtered_sendables = self.filter_sendables(sendables)
        if not filtered_sendables:
            return

        # The for loop works by iterating render types in self.render_types in order to ensure
        # execution order. This could be used for prioritizing certain render types over others,
        # depending on the protocol.
        for rt in self.render_types:
            if (data := filtered_sendables.get(rt, ())) and callable(
                method := getattr(self, f"handle_sendables_{rt}", None)
            ):
                method(data, metadata)

        self.at_after_sendables(sendables, metadata)

    def at_after_sendables(self, sendables: list["Any"], metadata: dict):
        """
        This is called after sendables are processed. use it for any cleanups or other processing.
        """
        pass

    def filter_sendables(self, sendables: list["Any"]) -> dict[str, list["Any"]]:
        out = defaultdict(list)
        for sendable in sendables:
            for render_type in getattr(sendable, "render_types", ()):
                if render_type in self.render_types:
                    out[render_type].append(sendable)
        return out

    def handle_sendables_oob(self, sendables: list, metadata: dict):
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
