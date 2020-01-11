"""
Auditable Server Sessions:
Extension of the stock ServerSession that yields objects representing
user inputs and system outputs.

Evennia contribution - Johnny 2017
"""
import os
import re
import socket

from django.utils import timezone
from django.conf import settings as ev_settings
from evennia.utils import utils, logger, mod_import, get_evennia_version
from evennia.server.serversession import ServerSession

# Attributes governing auditing of commands and where to send log objects
AUDIT_CALLBACK = getattr(
    ev_settings, "AUDIT_CALLBACK", "evennia.contrib.security.auditing.outputs.to_file"
)
AUDIT_IN = getattr(ev_settings, "AUDIT_IN", False)
AUDIT_OUT = getattr(ev_settings, "AUDIT_OUT", False)
AUDIT_ALLOW_SPARSE = getattr(ev_settings, "AUDIT_ALLOW_SPARSE", False)
AUDIT_MASKS = [
    {"connect": r"^[@\s]*[connect]{5,8}\s+(\".+?\"|[^\s]+)\s+(?P<secret>.+)"},
    {"connect": r"^[@\s]*[connect]{5,8}\s+(?P<secret>[\w]+)"},
    {"create": r"^[^@]?[create]{5,6}\s+(\w+|\".+?\")\s+(?P<secret>[\w]+)"},
    {"create": r"^[^@]?[create]{5,6}\s+(?P<secret>[\w]+)"},
    {"userpassword": r"^[@\s]*[userpassword]{11,14}\s+(\w+|\".+?\")\s+=*\s*(?P<secret>[\w]+)"},
    {"userpassword": r"^.*new password set to '(?P<secret>[^']+)'\."},
    {"userpassword": r"^.* has changed your password to '(?P<secret>[^']+)'\."},
    {"password": r"^[@\s]*[password]{6,9}\s+(?P<secret>.*)"},
] + getattr(ev_settings, "AUDIT_MASKS", [])


if AUDIT_CALLBACK:
    try:
        AUDIT_CALLBACK = getattr(
            mod_import(".".join(AUDIT_CALLBACK.split(".")[:-1])), AUDIT_CALLBACK.split(".")[-1]
        )
        logger.log_sec("Auditing module online.")
        logger.log_sec(
            "Audit record User input: {}, output: {}.\n"
            "Audit sparse recording: {}, Log callback: {}".format(
                AUDIT_IN, AUDIT_OUT, AUDIT_ALLOW_SPARSE, AUDIT_CALLBACK
            )
        )
    except Exception as e:
        logger.log_err("Failed to activate Auditing module. %s" % e)


class AuditedServerSession(ServerSession):
    """
    This particular implementation parses all server inputs and/or outputs and
    passes a dict containing the parsed metadata to a callback method of your
    creation. This is useful for recording player activity where necessary for
    security auditing, usage analysis or post-incident forensic discovery.

    *** WARNING ***
    All strings are recorded and stored in plaintext. This includes those strings
    which might contain sensitive data (create, connect, @password). These commands
    have their arguments masked by default, but you must mask or mask any
    custom commands of your own that handle sensitive information.

    See README.md for installation/configuration instructions.
    """

    def audit(self, **kwargs):
        """
        Extracts messages and system data from a Session object upon message
        send or receive.

        Kwargs:
            src (str): Source of data; 'client' or 'server'. Indicates direction.
            text (str or list): Client sends messages to server in the form of
                lists. Server sends messages to client as string.

        Returns:
            log (dict): Dictionary object containing parsed system and user data
                related to this message.

        """
        # Get time at start of processing
        time_obj = timezone.now()
        time_str = str(time_obj)

        session = self
        src = kwargs.pop("src", "?")
        bytecount = 0

        # Do not log empty lines
        if not kwargs:
            return {}

        # Get current session's IP address
        client_ip = session.address

        # Capture Account name and dbref together
        account = session.get_account()
        account_token = ""
        if account:
            account_token = "%s%s" % (account.key, account.dbref)

        # Capture Character name and dbref together
        char = session.get_puppet()
        char_token = ""
        if char:
            char_token = "%s%s" % (char.key, char.dbref)

        # Capture Room name and dbref together
        room = None
        room_token = ""
        if char:
            room = char.location
            room_token = "%s%s" % (room.key, room.dbref)

        # Try to compile an input/output string
        def drill(obj, bucket):
            if isinstance(obj, dict):
                return bucket
            elif utils.is_iter(obj):
                for sub_obj in obj:
                    bucket.extend(drill(sub_obj, []))
            else:
                bucket.append(obj)
            return bucket

        text = kwargs.pop("text", "")
        if utils.is_iter(text):
            text = "|".join(drill(text, []))

        # Mask any PII in message, where possible
        bytecount = len(text.encode("utf-8"))
        text = self.mask(text)

        # Compile the IP, Account, Character, Room, and the message.
        log = {
            "time": time_str,
            "hostname": socket.getfqdn(),
            "application": "%s" % ev_settings.SERVERNAME,
            "version": get_evennia_version(),
            "pid": os.getpid(),
            "direction": "SND" if src == "server" else "RCV",
            "protocol": self.protocol_key,
            "ip": client_ip,
            "session": "session#%s" % self.sessid,
            "account": account_token,
            "character": char_token,
            "room": room_token,
            "text": text.strip(),
            "bytes": bytecount,
            "data": kwargs,
            "objects": {
                "time": time_obj,
                "session": self,
                "account": account,
                "character": char,
                "room": room,
            },
        }

        # Remove any keys with blank values
        if AUDIT_ALLOW_SPARSE is False:
            log["data"] = {k: v for k, v in log["data"].items() if v}
            log["objects"] = {k: v for k, v in log["objects"].items() if v}
            log = {k: v for k, v in log.items() if v}

        return log

    def mask(self, msg):
        """
        Masks potentially sensitive user information within messages before
        writing to log. Recording cleartext password attempts is bad policy.

        Args:
            msg (str): Raw text string sent from client <-> server

        Returns:
            msg (str): Text string with sensitive information masked out.

        """
        # Check to see if the command is embedded within server output
        _msg = msg
        is_embedded = False
        match = re.match(".*Command.*'(.+)'.*is not available.*", msg, flags=re.IGNORECASE)
        if match:
            msg = match.group(1).replace("\\", "")
            submsg = msg
            is_embedded = True

        for mask in AUDIT_MASKS:
            for command, regex in mask.items():
                try:
                    match = re.match(regex, msg, flags=re.IGNORECASE)
                except Exception as e:
                    logger.log_err(regex)
                    logger.log_err(e)
                    continue

                if match:
                    term = match.group("secret")
                    masked = re.sub(term, "*" * len(term.zfill(8)), msg)

                    if is_embedded:
                        msg = re.sub(
                            submsg, "%s <Masked: %s>" % (masked, command), _msg, flags=re.IGNORECASE
                        )
                    else:
                        msg = masked

                    return msg

        return _msg

    def data_out(self, **kwargs):
        """
        Generic hook for sending data out through the protocol.

        Kwargs:
            kwargs (any): Other data to the protocol.

        """
        if AUDIT_CALLBACK and AUDIT_OUT:
            try:
                log = self.audit(src="server", **kwargs)
                if log:
                    AUDIT_CALLBACK(log)
            except Exception as e:
                logger.log_err(e)

        super(AuditedServerSession, self).data_out(**kwargs)

    def data_in(self, **kwargs):
        """
        Hook for protocols to send incoming data to the engine.

        Kwargs:
            kwargs (any): Other data from the protocol.

        """
        if AUDIT_CALLBACK and AUDIT_IN:
            try:
                log = self.audit(src="client", **kwargs)
                if log:
                    AUDIT_CALLBACK(log)
            except Exception as e:
                logger.log_err(e)

        super(AuditedServerSession, self).data_in(**kwargs)
