# In-Game Mail system

Contribution by grungies1138 2016

A simple Brandymail style mail system that uses the `Msg` class from Evennia
Core. It has two Commands for either sending mails between Accounts (out of game)
or between Characters (in-game). The two types of mails can be used together or
on their own.

   - `CmdMail` - this should sit on the Account cmdset and makes the `mail` command
    available both IC and OOC. Mails will always go to Accounts (other players).
   - `CmdMailCharacter` - this should sit on the Character cmdset and makes the `mail`
    command ONLY available when puppeting a character. Mails will be sent to other
    Characters only and will not be available when OOC.
   - If adding *both* commands to their respective cmdsets, you'll get two separate
    IC and OOC mailing systems, with different lists of mail for IC and OOC modes.

## Installation:

Install one or both of the following (see above):

- CmdMail (IC + OOC mail, sent between players)

    ```python
    # mygame/commands/default_cmds.py

    from evennia.contrib.game_systems import mail

    # in AccountCmdSet.at_cmdset_creation:
        self.add(mail.CmdMail())
    ```
- CmdMailCharacter (optional, IC only mail, sent between characters)

    ```python
    # mygame/commands/default_cmds.py

    from evennia.contrib.game_systems import mail

    # in CharacterCmdSet.at_cmdset_creation:
        self.add(mail.CmdMailCharacter())
    ```
Once installed, use `help mail` in game for help with the mail command. Use
ic/ooc to switch in and out of IC/OOC modes.


----

<small>This document page is generated from `evennia/contrib/game_systems/mail/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
