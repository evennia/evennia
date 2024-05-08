import pytz
from django.conf import settings

from evennia import AttributeProperty
from evennia.objects.objects import DefaultObject
from evennia.utils.eveditor import EvEditor
from evennia.utils import datetime_format, interactive
from evennia.utils.utils import class_from_module
from evennia.utils.ansi import strip_ansi
from evennia.utils.create import create_message
from evennia.comms.models import Msg

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)


class EvMessageBoard(DefaultObject):
    messages = AttributeProperty(dict, autocreate=False)
    message_id = AttributeProperty(0, autocreate=False)

    def at_object_creation(self):
        super().at_object_creation()

        self.locks.add("get:false();post:all();change:all();manage:perm(Builder)")
        self.tags.add("message_board", "contrib")
        self.db.desc = (
            "A board on which messages can be posted. Use the |hboard|n command to\n"
            "read and post to it (if you have the required permissions)."
        )

    def delete(self):
        Msg.objects.filter(db_receivers_objects=self).delete()
        return super().delete()


class CmdEvMessageBoard(COMMAND_DEFAULT_CLASS):
    """
    Read and post messages on a message board.

    Usage:
      board[/switches] [message #] [[subject] = message]

    Switches:
      unread - List only unread messages.
      read - Read the oldest unread message or a specific message.
      post - Post a new message.
      reply - Reply to a message.
      change - Change an existing message. This always uses the line editor.
      delete - Delete a message. Can be abbreviated to del.
      clear - Clear all messages from the board.
      edit - Use the line editor to compose the message.

    Examples:
      board/unread
      board/read
      board/read 1
      board/post Welcome = Welcome to the message board!
      board/post/edit
      board/reply 1 = Hello!
      board/reply/edit 1
      board/change 1
      board/delete 1
      board/clear

    With no arguments, all messages on the board will be listed.
    """

    key = "@board"
    aliases = ["@brd"]
    switch_options = ("read", "unread", "post", "reply", "change", "delete", "del", "clear", "edit")

    post_template = """
{separator}
|hFrom:|n {author} |h@|n {date_time} [|h#{message_id}|n]
{separator}
|hSubject:|n {subject}

{body}
{separator}
    """

    _MAX_SUBJECT_DISPLAY_LENGTH = 40

    def parse(self):
        super().parse()

    def func(self):
        boards = [
            obj
            for obj in self.caller.location.contents
            if obj.tags.has("message_board", category="contrib")
        ]

        if len(boards) == 0:
            self.caller.msg("There isn't a message board here.")
            return
        if len(boards) > 1:
            self.caller.msg("There is more than one message board here (and there shouldn't be.)")
            return

        board = boards[0]
        messages = _board_get_messages(board)
        use_editor = "edit" in self.switches

        if "read" in self.switches:
            if self.args:
                message_id = self.args.strip()
                if not (
                    message := self._get_message(board, message_id, "Usage: board/read [message #]")
                ):
                    return
            else:
                unread = {
                    id: message
                    for id, message in messages.items()
                    if not message.tags.has(self.caller.dbid, category="read_by")
                }
                if not unread:
                    self.caller.msg("You have read all the messages on this board.")
                    return

                message_id = next(iter(unread))
                message = messages[message_id]

            width = 78
            border_col = self.caller.account.options.get("border_color")
            separator_char = self.caller.account.options.get("separator_fill")
            separator = f"|{border_col}{separator_char * width}|n"

            author, subject = message.header.split("\n")
            body = message.message
            date_time = message.date_created

            self.caller.msg(
                self.format_post(message_id, separator, date_time, author, subject, body)
            )
            message.tags.add(self.caller.dbid, category="read_by")

            return

        if "post" in self.switches:
            if not board.access(self.caller, "post"):
                self.caller.msg("You are not allowed to post on this message board.")
                return

            if use_editor:
                self.start_editor(board)
                return

            if not (self.lhs and self.rhs):
                self.caller.msg("Usage: board/post topic = message")
                return

            board_post_message(self.caller, board, self.lhs, self.rhs)
            return

        if "reply" in self.switches:
            usage = (
                f"Usage: board/reply <message #> = <message>\n       board/reply/edit <message #>"
            )

            if "edit" in self.switches:
                if len(self.arglist) != 1 or self.rhs:
                    self.caller.msg(usage)
                    return
                message_id = self.arglist[0].strip()
                use_editor = True
            else:
                if not (self.lhs and self.rhs):
                    self.caller.msg(usage)
                    return
                message_id = self.lhs
                use_editor = False

            if not (message := self._get_message(board, message_id, usage)):
                return

            subject = message.header.split("\n")[1]
            subject = f"Re: {subject}"
            if use_editor:
                self.start_editor(board, subject=subject)
                return

            board_post_message(self.caller, board, subject, self.rhs)
            return

        if "change" in self.switches:
            can_post = board.access(self.caller, "post")
            can_change = board.access(self.caller, "change")
            can_manage = board.access(self.caller, "manage")

            if not ((can_post and can_change) or can_manage):
                self.caller.msg("You are not allowed to change posts on this message board.")
                return

            usage = "Usage: board/delete <message #>"
            message_id = self.args.strip()
            if not message_id.isdigit():
                self.caller.msg(usage)
                return

            if not (message := self._get_message(board, message_id, usage)):
                return

            if not (can_manage or self.caller in message["message"].senders):
                self.caller.msg("You may only change your own messages.")
                return

            subject = message.header.split("\n")[1]
            body = message.message
            self.start_editor(board, subject=subject, body=body, message_id=int(message_id))
            return

        if "delete" in self.switches or "del" in self.switches:
            can_post = board.access(self.caller, "post")
            can_change = board.access(self.caller, "change")
            can_manage = board.access(self.caller, "manage")

            if not ((can_post and can_change) or can_manage):
                self.caller.msg("You are not allowed to delete messages from this board.")
                return

            message_id = self.args.strip()
            if not (
                message := self._get_message(board, message_id, "Usage: board/delete <message #>")
            ):
                return

            if not (can_manage or self.caller in message["message"].senders):
                self.caller.msg("You may only delete your own messages.")
                return

            subject = message.header.split("\n")[1]
            answer = yield (
                f"Are you sure you want to delete the message '{subject}|n' (#{message_id}) yes/[no]?"
            )
            if not answer.lower() in ("yes", "y"):
                self.caller.msg("Cancelled. The message was not deleted.")
                return

            message.delete()
            del board.messages[int(message_id)]
            self.caller.msg(f"Message #{message_id} deleted.")

            return

        if "clear" in self.switches:
            if not board.access(self.caller, "manage"):
                self.caller.msg("You are not allowed to clear this message board.")
                return

            answer = yield ("Are you sure you want to clear all messages from the board yes/[no]?")
            if not answer.lower() in ("yes", "y"):
                self.caller.msg("Cancelled. The message board was not cleared.")
                return

            Msg.objects.filter(db_receivers_objects=board).delete()
            board.messages.clear()
            board.message_id = 0
            self.caller.msg("The message board has been cleared.")

            return

        # List messages
        if messages:
            if "unread" in self.switches:
                messages = {
                    message_id: message
                    for message_id, message in messages.items()
                    if not message.tags.get(self.caller.dbid, category="read_by")
                }
                if not messages:
                    self.caller.msg("You have read all the messages on this board.")
                    return

            table = self.create_table()
            time_zone = self.caller.account.options.get("timezone")
            for message_id, message in messages.items():
                unread_mark = "" if message.tags.get(self.caller.dbid, category="read_by") else "*"
                author, subject = message.header.split("\n")
                if len(subject) > self._MAX_SUBJECT_DISPLAY_LENGTH:
                    subject = subject[: self._MAX_SUBJECT_DISPLAY_LENGTH] + "..."
                time = datetime_format(self._utc_to_local(message.date_created, time_zone))
                self.add_table_row(
                    table, f"{unread_mark}{message_id}", author, subject, time
                )

            self.format_table(table)
            string = self.get_table_header(board) + str(table) + self.get_table_footer(board)
        else:
            string = (
                f"There are no messages on this board yet.  {self.get_can_can_post_info(board)}."
            )
        self.msg(string)

    def start_editor(self, board, subject=None, body=None, message_id=None):
        """
        (WIP)
        subject required if replying
        buf and message_id (but not subject) required for editing (this will be changed)

        Edit should call the module's
          board_post_message(caller, board, subject, body, message_id=None)
        """

        self._send_editor_intructions()
        self.caller.db.message_board = board
        self.caller.db.message_board_buf = ""
        if subject:
            self.caller.db.message_board_buf = f"{subject}\n"
        if body:
            self.caller.db.message_board_buf += f"\n{body}"
        if message_id:
            self.caller.db.message_board_message_id = message_id

        EvEditor(
            self.caller,
            loadfunc=_board_editor_load,
            savefunc=_board_editor_save,
            quitfunc=_board_editor_quit,
            key="board message",
            persistent=True,
        )

    def format_post(self, message_id, separator, date_time, author, subject, body):
        time_zone = self.caller.account.options.get("timezone")
        date_time = self._utc_to_local(date_time, time_zone).strftime("%Y-%m-%d %H:%M:%S")

        return self.post_template.format(
            separator=separator,
            message_id=message_id,
            date_time=date_time,
            author=author,
            subject=subject,
            body=body,
        ).strip()

    def create_table(self):
        """
        (WIP)
        table must override __str__()
        """
        return self.styled_table("#", "From", "Subject", "Posted")

    def add_table_row(self, table, message_id, author, subject, date_time):
        table.add_row(message_id, author, subject, date_time)

    def format_table(self, table):
        table.reformat_column(0, align="r")

    def get_table_header(self, board):
        return ""

    def get_table_footer(self, board):
        return f"\n  * Indicates an unread message.  {self.get_can_can_post_info(board)}."

    def get_can_can_post_info(self, board):
        return (
            "You |gmay post|n on this message board"
            if board.access(self.caller, "post")
            else "You |rmay not post|n on this message board"
        )

    def _utc_to_local(self, utc_time, time_zone):
        if not time_zone:
            return utc_time
        # don't convert a time that's not UTC
        if utc_time.utcoffset().total_seconds() != 0:
            return utc_time

        return utc_time.replace(tzinfo=pytz.utc).astimezone(time_zone)

    def _get_message(self, board, message_id, usage):
        if not message_id.isdigit():
            self.caller.msg(usage)
            return None

        message_id = int(message_id)
        if not (message := board.messages.get(message_id)):
            self.caller.msg(f"There is no message #{message_id}.")
            return None

        return message

    def _send_editor_intructions(self):
        string = (
            "|yUse the line editor to enter your message. The first line containing\n"
            "text will be used as the subject.\n"
            "\n"
            "To post the message, save it (:w) then quit (:q). If you have saved a\n"
            "message you can cancel posting it by clearing the message (:DD) then\n"
            "saving and quitting.|n\n"
        )
        self.caller.msg(string)


def _board_get_messages(board):
    if not (messages := board.db.messages):
        board.db.messages = {}
        messages = board.db.messages

    return messages


def _board_editor_load(caller):
    buf = caller.db.message_board_buf or ""
    caller.attributes.remove("message_board_buf")

    return buf


def _board_editor_save(caller, buf):
    if buf:
        if len([line for line in buf.split("\n") if line.strip()]) < 2:
            caller.msg("|rYour message must contain at least a subject line and a body line.|n")
            return False
        caller.msg("Message saved for posting.")
    else:
        caller.msg("|yMessage will not be posted.|n")

    caller.db.message_board_buf = buf
    return True


def _board_editor_quit(caller):
    message = caller.db.message_board_buf
    if not message:
        caller.msg("Posting cancelled.")
        return

    lines = message.strip().split("\n")
    subject = lines[0]
    body = "\n".join(lines[1:]).strip()

    message_id = caller.db.message_board_message_id
    if message_id:
        board_post_message(caller, caller.db.message_board, subject, body, message_id=message_id)
    else:
        board_post_message(caller, caller.db.message_board, subject, body)

    caller.attributes.remove("message_board")
    caller.attributes.remove("message_board_buf")
    caller.attributes.remove("message_board_message_id")


def board_post_message(caller, board, subject, body, message_id=None):
    if not caller.permissions.check("Builder"):
        subject = strip_ansi(subject)

    if message_id is None:
        message = create_message(
            caller,
            body,
            header=f"{caller.key}\n{subject}",
            receivers=board,
            tags=[
                ("board_message", "comms"),
                (caller.dbid, "read_by")
            ]
        )

        message_id = board.message_id + 1
        board.message_id = message_id
        board.messages[message_id] = message

        caller.msg(f"Your message '{subject}|n' has been posted.")
    else:
        messages = _board_get_messages(board)
        if not (message := messages.get(message_id)):
            caller.msg(f"Message #{message_id} has been deleted. Change cancelled.")
            return

        author = message.header.split('\n')[0]
        message.header = f"{author}\n{subject}"
        message.message = body
        caller.msg(f"Message #{message_id} has been changed.")
