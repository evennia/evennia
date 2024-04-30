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

        self.locks.add("get:false();brdpost:all();brdchange:all();brdmanage:perm(Builder)")
        self.tags.add("message_board", "contrib")
        self.db.desc = (
            "A board on which messages can be posted. Use the |hboard|n command to "
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
                    if self.caller not in message["read_by"]
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

            msg = message["message"]
            time_zone = self.caller.account.options.get("timezone")
            date_time = self._utc_to_local(msg.date_created, time_zone).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            info = (
                f"|{border_col}From:|n "
                f"{message['author_name']} |{border_col}@|n "
                f"{date_time} |{border_col}[#{message_id}]|n"
            )

            lines = msg.message.split("\n")
            subject = f"|{border_col}Subject:|n {lines[0]}"
            body = "\n".join(lines[1:])

            self.caller.msg(
                f"{separator}\n"
                f"{info}\n"
                f"{separator}\n"
                f"|h{subject}|n\n\n"
                f"{body}\n"
                f"{separator}"
            )
            message["read_by"].add(self.caller)

            return

        if "post" in self.switches:
            if not board.access(self.caller, "brdpost"):
                self.caller.msg("You are not allowed to post on this message board.")
                return
            if use_editor:
                self._send_editor_intructions()
                self.caller.db.message_board = board
                EvEditor(
                    self.caller,
                    loadfunc=_board_editor_load,
                    savefunc=_board_editor_save,
                    quitfunc=_board_editor_quit,
                    key="board message",
                    persistent=True
                )
                return
            else:
                if not (self.lhs and self.rhs):
                    self.caller.msg("Usage: board/post topic = message")
                    return
                _board_post_message(self.caller, board, self.lhs, self.rhs)

            return

        if "reply" in self.switches:
            usage = (
                "Usage: board/reply <message #> = <message>\n"
                "       board/reply/edit <message #>"
            )

            if "edit" in self.switches:
                if len(self.arglist) != 1 or self.rhs:
                    self.caller.msg(usage)
                    return
                use_editor = True
            else:
                if len(self.arglist) < 1 or not self.rhs:
                    self.caller.msg(usage)
                    return
                use_editor = False

            message_id = self.arglist[0].strip()
            if not (message := self._get_message(board, message_id, usage)):
                return

            subject = message["message"].message.split("\n")[0]
            subject = f"Re: {subject}"
            if use_editor:
                self._send_editor_intructions()
                self.caller.db.message_board = board
                self.caller.db.message_board_buf = subject
                EvEditor(
                    self.caller,
                    loadfunc=_board_editor_load,
                    savefunc=_board_editor_save,
                    quitfunc=_board_editor_quit,
                    key="board message",
                    persistent=True
                )
                return

            _board_post_message(self.caller, board, subject, self.rhs)
            return

        if "change" in self.switches:
            can_post = board.access(self.caller, "brdpost")
            can_change = board.access(self.caller, "brdchange")
            can_manage = board.access(self.caller, "brdmanage")

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

            self._send_editor_intructions()
            self.caller.db.message_board = board
            self.caller.db.message_board_buf = message["message"].message
            self.caller.db.message_board_message_id = int(message_id)
            EvEditor(
                self.caller,
                loadfunc=_board_editor_load,
                savefunc=_board_editor_save,
                quitfunc=_board_editor_quit,
                key="board message",
                persistent=True
            )

            return

        if "delete" in self.switches or "del" in self.switches:
            can_post = board.access(self.caller, "brdpost")
            can_change = board.access(self.caller, "brdchange")
            can_manage = board.access(self.caller, "brdmanage")

            if not ((can_post and can_change) or can_manage):
                self.caller.msg("You are not allowed to delete messages from this board.")
                return

            message_id = self.args.strip()
            if not message_id.isdigit():
                self.caller.msg("Usage: board/delete <message #>")
                return

            if not (
                message := self._get_message(board, message_id, "Usage: board/delete <message #>")
            ):
                return

            if not (can_manage or self.caller in message["message"].senders):
                self.caller.msg("You may only delete your own messages.")
                return

            self._delete_message(self.caller, board, int(message_id))
            return

        if "clear" in self.switches:
            if not board.access(self.caller, "brdmanage"):
                self.caller.msg("You are not allowed to clear this message board.")
                return

            self._clear_board(self.caller, board)
            return

        # List messages
        can_post = (
            "You |gmay post|n on this message board"
            if board.access(self.caller, "brdpost")
            else "You |rmay not post|n on this message board"
        )

        if messages:
            if "unread" in self.switches:
                # messages = [message for message in messages if self.caller not in message["read_by"]]
                messages = {
                    message_id: message
                    for message_id, message in messages.items()
                    if not self.caller in message["read_by"]
                }
                if not messages:
                    self.caller.msg("You have read all the messages on this board.")
                    return

            table = self.styled_table("#", "From", "Subject", "Posted")
            time_zone = self.caller.account.options.get("timezone")
            for message_id, message in messages.items():
                unread_mark = "" if self.caller in message["read_by"] else "*"
                subject = message["subject"]
                time = datetime_format(self._utc_to_local(message["post_date"], time_zone))
                if len(subject) > self._MAX_SUBJECT_DISPLAY_LENGTH:
                    subject = subject[:self._MAX_SUBJECT_DISPLAY_LENGTH] + "..."
                table.add_row(f"{unread_mark}{message_id}", message["author_name"], subject, time)
                table.reformat_column(0, align="r")

            string = str(table) + f"\n  * Indicates an unread message.  {can_post}."
        else:
            string = f"There are no messages on this board yet. {can_post}."
        self.msg(string)

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

    @interactive
    def _delete_message(self, caller, board, message_id):
        message = board.messages[message_id]["message"]
        subject = message.message.split("\n")[0]
        answer = yield (
            f"Are you sure you want to delete the message '{subject}|n' (#{message_id}) yes/[no]?"
        )
        if not answer.lower() in ("yes", "y"):
            caller.msg("Cancelled.")
            return

        message.delete()
        del board.messages[message_id]
        caller.msg(f"Message #{message_id} deleted.")

    @interactive
    def _clear_board(self, caller, board):
        answer = yield ("Are you sure you want to clear all messages from the board yes/[no]?")
        if not answer.lower() in ("yes", "y"):
            caller.msg("Cancelled.")
            return

        Msg.objects.filter(db_receivers_objects=board).delete()
        board.messages.clear()
        board.message_id = 0
        caller.msg("Message board cleared.")


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
        _board_post_message(caller, caller.db.message_board, subject, body, message_id=message_id)
    else:
        _board_post_message(caller, caller.db.message_board, subject, body)

    caller.attributes.remove("message_board")
    caller.attributes.remove("message_board_buf")
    caller.attributes.remove("message_board_message_id")


def _board_post_message(caller, board, subject, body, message_id=None):
    if not caller.permissions.check("Builder"):
        subject = strip_ansi(subject)

    if message_id is None:
        msg = create_message(
            caller, subject + "\n" + body, receivers=board, tags=[("board_message", "comms")]
        )
        message = {
            "post_date": msg.date_created,
            "author_name": caller.key,
            "subject": subject,
            "message": msg,
            "read_by": {caller}
        }

        message_id = board.message_id + 1
        board.message_id = message_id
        board.messages[message_id] = message

        caller.msg(f"Your message '{subject}|n' has been posted.")
    else:
        messages = _board_get_messages(board)
        if not (message := messages.get(message_id)):
            caller.msg(f"Message #{message_id} has been deleted. Change cancelled.")
            return

        message["subject"] = subject
        message["message"].message = subject + "\n" + body
        caller.msg(f"Message #{message_id} has been changed.")
