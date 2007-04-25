INSERT INTO "helpsys_helpentry" VALUES(1,'Help Index','This game has yet to customize its help index, so for now you may browse the generic codebase help files.

Topics
------
NEWBIE %%t%%t Getting started (for new players).
COMMANDS %%t How to get help with commands.
CREDITS %%t Codebase credits.',0);
INSERT INTO "helpsys_helpentry" VALUES(2,'Credits','Evennia is a product of a small community of developers, all working towards the continual improvement of the codebase. The following people have made major contributions with the end result being what you are now playing.

"Kelvin" (Greg Taylor) - Lead developer and original author.',0);
INSERT INTO "helpsys_helpentry" VALUES(3,'Commands','Commands in Evennia are generally organized into one of two categories: %%cgPublic%%cn or %%cyPrivileged%%cn commands.

%%cgPublic%%cn commands are more or less available to everyone. None of these commands are prefixed with anything, they are typical, every-day commands like %%chlook%%cn, %%chsay%%cn, and %%chget%%cn.

%%cyPrivileged%%cn command availability is largely dependent on the privileges and powers bestowed on you by the staff. Privileged commands are generally building/administration related and aren''t of general interest to players. These commands are all pre-fixed by a ''%%ch@%%cn'' character.

To see a list of all commands, use %%ch@list commands%%cn. If you''d like to learn more about any individual command, you may do so by typing %%chhelp <topic>%%cn, where <topic> is the name of the command (without the <>''s).',0);