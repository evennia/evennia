"""
In-Game Mail system

Evennia Contribution - grungies1138 2016

A simple Brandymail style @mail system that uses the Msg class from Evennia Core.

Installation:
    import CmdMail from this module (from evennia.contrib.mail import CmdMail),
    and add into the default Player or Character command set (self.add(CmdMail)).

"""

import re
from evennia import ObjectDB, PlayerDB
from evennia import default_cmds
from evennia.utils import create, evtable, make_iter
from evennia.comms.models import Msg


_HEAD_CHAR = "|015-|n"
_SUB_HEAD_CHAR = "-"
_WIDTH = 78

class CmdMail(default_cmds.MuxCommand):
    """
    Commands that allow either IC or OOC communications

    Usage:
        @mail       - Displays all the mail a player has in their mailbox

        @mail <#>   - Displays a specific message

        @mail <players>=<subject>/<message>
                - Sends a message to the comma separated list of players.

        @mail/delete <#> - Deletes a specific message

        @mail/forward <player list>=<#>[/<Message>]
                - Forwards an existing message to the specified list of players,
                  original message is delivered with optional Message prepended.

        @mail/reply <#>=<message>
                - Replies to a message #.  Prepends message to the original
                  message text.
    Switches:
        delete  - deletes a message
        forward - forward a received message to another object with an optional message attached.
        reply   - Replies to a received message, appending the original message to the bottom.

    Examples:
        @mail 2
        @mail Griatch=New mail/Hey man, I am sending you a message!
        @mail/delete 6
        @mail/forward feend78 Griatch=4/You guys should read this.
        @mail/reply 9=Thanks for the info!
    """
    key = "@mail"
    aliases = ["mail"]
    lock = "cmd:all()"
    help_category = "General"

    def search_targets(self, namelist):
        """
        Search a list of targets of the same type as caller.

        Args:
            caller (Object or Player): The type of object to search.
            namelist (list): List of strings for objects to search for.

        Returns:
            targetlist (list): List of matches, if any.

        """
        nameregex = r"|".join(r"^%s$" % re.escape(name) for name in make_iter(namelist))
        if hasattr(self.caller, "player") and self.caller.player:
            matches = list(ObjectDB.objects.filter(db_key__iregex=nameregex))
        else:
            matches = list(PlayerDB.objects.filter(username__iregex=nameregex))
        return matches

    def get_all_mail(self):
        """
        Returns a list of all the messages where the caller is a recipient.

        Returns:
            messages (list): list of Msg objects.
        """
        # mail_messages = Msg.objects.get_by_tag(category="mail")
        # messages = []
        try:
            player = self.caller.player
        except AttributeError:
            player = self.caller
        messages = Msg.objects.get_by_tag(category="mail", raw_queryset=True).filter(db_receivers_players=player)
        return messages

    def send_mail(self, recipients, subject, message, caller):
        """
        Function for sending new mail.  Also useful for sending notifications from objects or systems.

        Args:
            recipients (list): list of Player or character objects to receive the newly created mails.
            subject (str): The header or subject of the message to be delivered.
            message (str): The body of the message being sent.
            caller (obj): The object (or Player or Character) that is sending the message.
        """
        for recipient in recipients:
            recipient.msg("You have received a new @mail from %s" % caller)
            new_message = create.create_message(self.caller, message, receivers=recipient, header=subject)
            new_message.tags.add("U", category="mail")

        if recipients:
            caller.msg("You sent your message.")
            return
        else:
            caller.msg("No valid players found.  Cannot send message.")
            return

    def func(self):
        subject = ""
        body = ""

        if self.switches or self.args:
            if "delete" in self.switches:
                try:
                    if not self.lhs:
                        self.caller.msg("No Message ID given.  Unable to delete.")
                        return
                    else:
                        all_mail = self.get_all_mail()
                        mind = int(self.lhs) - 1
                        if all_mail[mind]:
                            all_mail[mind].delete()
                            self.caller.msg("Message %s deleted" % self.lhs)
                        else:
                            raise IndexError
                except IndexError:
                    self.caller.msg("That message does not exist.")
                except ValueError:
                    self.caller.msg("Usage: @mail/delete <message ID>")
            elif "forward" in self.switches:
                try:
                    if not self.rhs:
                        self.caller.msg("Cannot forward a message without a player list.  Please try again.")
                        return
                    elif not self.lhs:
                        self.caller.msg("You must define a message to forward.")
                        return
                    else:
                        all_mail = self.get_all_mail()
                        if "/" in self.rhs:
                            message_number, message = self.rhs.split("/")
                            mind = int(message_number) - 1

                            if all_mail[mind]:
                                old_message = all_mail[mind]

                                self.send_mail(self.search_targets(self.lhslist), "FWD: " + old_message.header,
                                               message + "\n---- Original Message ----\n" + old_message.message,
                                               self.caller)
                                self.caller.msg("Message forwarded.")
                            else:
                                raise IndexError
                        else:
                            mind = int(self.rhs) - 1
                            if all_mail[mind]:
                                old_message = all_mail[mind]
                                self.send_mail(self.search_targets(self.lhslist), "FWD: " + old_message.header,
                                               "\n---- Original Message ----\n" + old_message.message, self.caller)
                                self.caller.msg("Message forwarded.")
                                old_message.tags.remove("u", category="mail")
                                old_message.tags.add("f", category="mail")
                            else:
                                raise IndexError
                except IndexError:
                    self.caller.msg("Message does not exixt.")
                except ValueError:
                    self.caller.msg("Usage: @mail/forward <player list>=<#>[/<Message>]")
            elif "reply" in self.switches:
                try:
                    if not self.rhs:
                        self.caller.msg("You must define a message to reply to.")
                        return
                    elif not self.lhs:
                        self.caller.msg("You must supply a reply message")
                        return
                    else:
                        all_mail = self.get_all_mail()
                        mind = int(self.lhs) - 1
                        if all_mail[mind]:
                            old_message = all_mail[mind]
                            self.send_mail(old_message.senders, "RE: " + old_message.header,
                                           self.rhs + "\n---- Original Message ----\n" + old_message.message, self.caller)
                            old_message.tags.remove("u", category="mail")
                            old_message.tags.add("r", category="mail")
                            return
                        else:
                            raise IndexError
                except IndexError:
                    self.caller.msg("Message does not exist.")
                except ValueError:
                    self.caller.msg("Usage: @mail/reply <#>=<message>")
            else:
                # normal send
                if self.rhs:
                    if "/" in self.rhs:
                        subject, body = self.rhs.split("/", 1)
                    else:
                        body = self.rhs
                    self.send_mail(self.search_targets(self.lhslist), subject, body, self.caller)
                else:
                    try:
                        message = self.get_all_mail()[int(self.lhs) - 1]
                    except (ValueError, IndexError):
                        self.caller.msg("'%s' is not a valid mail id." % self.lhs)
                        return

                    messageForm = []
                    if message:
                        messageForm.append(_HEAD_CHAR * _WIDTH)
                        messageForm.append("|wFrom:|n %s" % (message.senders[0].key))
                        messageForm.append("|wSent:|n %s" % message.db_date_created.strftime("%m/%d/%Y %H:%M:%S"))
                        messageForm.append("|wSubject:|n %s" % message.header)
                        messageForm.append(_SUB_HEAD_CHAR * _WIDTH)
                        messageForm.append(message.message)
                        messageForm.append(_HEAD_CHAR * _WIDTH)
                    self.caller.msg("\n".join(messageForm))
                    message.tags.remove("u", category="mail")
                    message.tags.add("o", category="mail")

        else:
            messages = self.get_all_mail()

            if messages:
                table = evtable.EvTable("|wID:|n", "|wFrom:|n", "|wSubject:|n", "|wDate:|n", "|wSta:|n",
                                        table=None, border="header", header_line_char=_SUB_HEAD_CHAR, width=_WIDTH)
                index = 1
                for message in messages:
                    table.add_row(index, message.senders[0], message.header,
                                  message.db_date_created.strftime("%m/%d/%Y"),
                                  str(message.db_tags.last().db_key.upper()))
                    index += 1

                table.reformat_column(0, width=6)
                table.reformat_column(1, width=17)
                table.reformat_column(2, width=34)
                table.reformat_column(3, width=13)
                table.reformat_column(4, width=7)

                self.caller.msg(_HEAD_CHAR * _WIDTH)
                self.caller.msg(unicode(table))
                self.caller.msg(_HEAD_CHAR * _WIDTH)
            else:
                self.caller.msg("There are no messages in your inbox.")

