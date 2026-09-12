/*
 * Aetos in-client help.
 *
 * Documentation a player can read without leaving the game, opened with F1 or
 * from the command palette.
 *
 * WHY IN THE CLIENT AT ALL. Aetos has features a player cannot discover by
 * looking -- an alias engine, a scripting language, a private notes store. A
 * README on a website does not help someone who is already logged in and
 * wondering what Ctrl+K did. Documentation that lives beside the thing it
 * documents is the only kind that gets read.
 *
 * WHAT IS DOCUMENTED IS WHAT EXISTS. Topics are gated on the same automation
 * policy as the editors themselves (blueprint section 32). On a game that
 * forbids scripting there is no scripting topic -- documenting a feature the
 * player cannot use is a worse failure than not documenting it, because it
 * sends them looking for a button that is not there.
 *
 * ACCESSIBILITY. Two panes, both reachable by keyboard: a topic list and the
 * article. Choosing a topic moves focus into the article, so a screen-reader
 * user lands on the content rather than having to hunt for where it appeared.
 * Escape closes and focus returns to whatever opened it.
 */

(function (window, document) {
    "use strict";

    /* ------------------------------------------------------------------
     * Content
     *
     * Each topic is data, not markup. `body` entries are paragraphs, `code`
     * entries are literal blocks, and `keys` entries are keyboard tables. This
     * keeps every topic rendered identically and makes the whole set
     * searchable without parsing HTML.
     * ------------------------------------------------------------------ */

    var TOPICS = [
        {
            id: "start",
            title: "Getting started",
            group: "Basics",
            summary: "What Aetos is and how to find everything in it.",
            sections: [
                {
                    body: [
                        "Aetos is a graphical client for this game. Everything it shows you " +
                            "comes from the game itself, and every button sends an ordinary " +
                            "command -- the same one you could type. Nothing here lets you do " +
                            "anything you could not do at the command line.",
                        "The panels around the main window are widgets. Which ones you see " +
                            "depends on what this game exposes: a game with no resource system " +
                            "shows no resource bars, rather than showing empty ones."
                    ]
                },
                {
                    heading: "The three things worth learning first",
                    keys: [
                        ["Ctrl+K", "Open the command palette -- every client action, searchable"],
                        ["F1", "Open this help"],
                        ["Ctrl+Shift+L", "Edit your layout: move, resize and hide panels"]
                    ]
                },
                {
                    heading: "Where your settings live",
                    body: [
                        "In this browser, and nowhere else. Your layouts, macros, aliases, " +
                            "notes and tags are never sent to the game server. See the Privacy " +
                            "topic for exactly what is stored and how to export or delete it."
                    ]
                }
            ]
        },

        {
            id: "layout",
            title: "Layout and workspaces",
            group: "Basics",
            summary: "Rearranging panels, and saving arrangements you can switch between.",
            sections: [
                {
                    body: [
                        "Press Ctrl+Shift+L to enter layout editing. Each panel gains controls " +
                            "to move it between regions, resize it and hide it. Everything is " +
                            "operable from the keyboard -- dragging is an alternative, never a " +
                            "requirement.",
                        "Hiding a panel is your choice and it stays hidden. That is separate " +
                            "from a panel that hides itself because it has nothing to show: an " +
                            "empty inventory does not leave a blank box on your screen."
                    ]
                },
                {
                    heading: "Workspaces",
                    body: [
                        "A workspace is a named layout. Save one for exploring and another for " +
                            "combat and switch between them, rather than rearranging panels " +
                            "every time you change what you are doing.",
                        "Workspaces are per-browser, like everything else Aetos stores."
                    ]
                },
                {
                    heading: "Different screens",
                    body: [
                        "Aetos measures its own container, not the browser window, and adapts " +
                            "at four sizes: phone, tablet, desktop and wide. On a phone the " +
                            "side panels become horizontally swipeable strips so the map does " +
                            "not get buried under everything else."
                    ]
                }
            ]
        },

        {
            id: "palette",
            title: "Command palette",
            group: "Basics",
            summary: "Ctrl+K: every client action in one searchable list.",
            sections: [
                {
                    body: [
                        "The palette acts on the client, never on the game. It will not send " +
                            "commands -- you already have a command line for that, and a second " +
                            "one that looked similar but behaved differently would be a trap.",
                        "Matching is forgiving: typing \"elay\" finds \"Edit layout\". You do " +
                            "not have to remember the exact name, only some of the letters in " +
                            "order."
                    ]
                },
                {
                    heading: "Keys",
                    keys: [
                        ["Ctrl+K / Cmd+K", "Open, from anywhere including the game input"],
                        ["Up / Down", "Move through results"],
                        ["Home / End", "Jump to first or last"],
                        ["Enter", "Run the selected action"],
                        ["Escape", "Close, returning focus where it was"]
                    ]
                },
                {
                    heading: "It teaches shortcuts",
                    body: [
                        "Entries show their keyboard shortcut. A shortcut nobody can find is " +
                            "not a feature, so the palette is where you learn them rather than " +
                            "having to read documentation you did not know existed."
                    ]
                }
            ]
        },

        {
            id: "macros",
            title: "Macros and the hotbar",
            group: "Automation",
            requires: "macros",
            summary: "Buttons that send up to five commands in order.",
            sections: [
                {
                    body: [
                        "A macro is a labelled button holding up to five commands. They are " +
                            "sent one at a time through the ordinary command path, so every " +
                            "lock, cooldown and permission applies exactly as if you typed " +
                            "them.",
                        "Five is a deliberate limit. A macro is a shortcut for something you " +
                            "do constantly, not a script -- if you need branching or " +
                            "conditions, that is what Aetos Script is for."
                    ]
                },
                {
                    heading: "Example",
                    example: "Label:    Recover\nCommands: quaff healing potion\n" +
                        "          sit\n          rest"
                },
                {
                    heading: "The queue",
                    body: [
                        "Anything that sends more than one command -- a macro, a map route, a " +
                            "script -- goes through a queue you can watch and stop. \"Stop " +
                            "queued commands\" in the palette cancels whatever is running.",
                        "The queue paces commands rather than flooding the server. It is not a " +
                            "way around a cooldown; the server still refuses anything too soon."
                    ]
                }
            ]
        },

        {
            id: "aliases",
            title: "Aliases",
            group: "Automation",
            requires: "aliases",
            summary: "Shorthand for commands you type constantly.",
            sections: [
                {
                    body: [
                        "An alias replaces the first word of what you type. Arguments are " +
                            "substituted with $1, $2 and so on for individual words, and $* " +
                            "for everything that is left."
                    ]
                },
                {
                    heading: "Examples",
                    example:
                        "Pattern: tt\nSends:   tell $1 $*\n" +
                        "Typing:  tt Bob hello there\nBecomes: tell Bob hello there\n\n" +
                        "Pattern: k\nSends:   kill $*\n" +
                        "Typing:  k the goblin\nBecomes: kill the goblin"
                },
                {
                    heading: "What aliases cannot do",
                    body: [
                        "An alias cannot expand into another alias, so a pair of aliases " +
                            "cannot loop forever. And it cannot reach a command you do not " +
                            "have -- the expansion is sent exactly as though you typed it, and " +
                            "the server decides."
                    ]
                }
            ]
        },

        {
            id: "triggers",
            title: "Triggers",
            group: "Automation",
            requires: "triggers",
            summary: "Run commands when the game says something.",
            sections: [
                {
                    body: [
                        "A trigger watches output and fires commands when it matches. Match on " +
                            "plain text, or on a regular expression when you need to capture " +
                            "part of the line.",
                        "Prefer structured triggers where this game offers them. Text matching " +
                            "breaks the moment a game rewords a message, and you will not " +
                            "notice until the trigger silently stops firing."
                    ]
                },
                {
                    heading: "Example",
                    example:
                        "Name:     Flee when hurt\nWhen the game says: You are badly wounded\n" +
                        "Then run: flee"
                },
                {
                    heading: "Rate limiting",
                    body: [
                        "A trigger will not fire again immediately on the same match. Without " +
                            "that, a message repeated by the game would produce a storm of " +
                            "commands -- which looks exactly like an attack on the server, and " +
                            "is treated as one by most games."
                    ]
                },
                {
                    heading: "Check the rules",
                    body: [
                        "Triggers act on your behalf. Many games have rules about automated " +
                            "reactions, particularly in combat. This game has allowed the " +
                            "feature; that is not the same as allowing every use of it."
                    ]
                }
            ]
        },

        {
            id: "timers",
            title: "Timers",
            group: "Automation",
            requires: "timers",
            summary: "Run commands on a schedule.",
            sections: [
                {
                    body: [
                        "A timer runs up to five commands every so many seconds, either once " +
                            "or repeatedly. Timers run while you are not typing, which is the " +
                            "whole point and also the thing to be careful about."
                    ]
                },
                {
                    heading: "Example",
                    example: "Name:     Upkeep\nEvery:    300 seconds\nRepeat:   yes\n" +
                        "Run:      renew ward"
                },
                {
                    heading: "Unattended play",
                    body: [
                        "This game has enabled timers, but many games have rules about acting " +
                            "while away from the keyboard. Check them. Aetos will not stop you, " +
                            "and a moderator is a worse way to find out."
                    ]
                }
            ]
        },

        {
            id: "scripting",
            title: "Aetos Script",
            group: "Automation",
            requires: "scripting",
            summary: "A small, deliberately limited scripting language.",
            sections: [
                {
                    body: [
                        "Aetos Script is a real language with variables, conditions and loops, " +
                            "run by an interpreter written for this purpose. It is not " +
                            "JavaScript and it is not evaluated as JavaScript -- the grammar " +
                            "has no property access, no indexing and no way to define " +
                            "functions, so there is nothing to escape from.",
                        "A script cannot reach the web, your files, the page, or anything on " +
                            "your computer. It can call the handful of functions below and " +
                            "nothing else."
                    ]
                },
                {
                    heading: "What a script can call",
                    example:
                        'send("look")             -- send a command, as if typed\n' +
                        'echo("text")             -- print locally; the game never sees it\n' +
                        'resource("health")       -- 0.0 to 1.0, or null if unknown\n' +
                        "room()                   -- the current room name\n" +
                        "target()                 -- the current target name, or null\n" +
                        'get("key")               -- read one of your saved variables\n' +
                        'set("key", value)        -- save a variable in this browser'
                },
                {
                    heading: "Example",
                    example:
                        'if resource("health") < 0.3 then\n' +
                        '  send("quaff potion")\n' +
                        '  echo("Getting low.")\n' +
                        "end\n\n" +
                        "let count = 0\n" +
                        "while count < 3 do\n" +
                        '  send("search")\n' +
                        "  let count = count + 1\n" +
                        "end"
                },
                {
                    heading: "Limits, and why they exist",
                    body: [
                        "A script stops after 10,000 steps, 1,000 iterations of any one loop, " +
                            "16 levels of nesting or a quarter of a second of running time, " +
                            "whichever comes first. A runaway script freezes the tab it runs " +
                            "in, which is your tab -- these limits protect you, not the server.",
                        "Everything a script sends still travels the ordinary command path. A " +
                            "script has no authority a typed command lacks."
                    ]
                }
            ]
        },

        {
            id: "map",
            title: "The map",
            group: "The world",
            summary: "Where you are, what is nearby, and walking there.",
            sections: [
                {
                    body: [
                        "The map is built by walking the exits you can actually see, so hidden " +
                            "exits stay hidden. It needs no cooperation from the game, though a " +
                            "game that supplies coordinates gets a more accurate picture.",
                        "Clicking a room walks you there by sending the ordinary movement " +
                            "commands one at a time. The server decides each step, so a locked " +
                            "door stops the route exactly where it should."
                    ]
                },
                {
                    heading: "Without looking at it",
                    body: [
                        "Every map has a written equivalent generated from the same data, so " +
                            "the picture and the description can never disagree. It lists your " +
                            "current room, the exits and their destinations, and what is nearby " +
                            "with distances -- which is often faster to read than the diagram " +
                            "is to look at."
                    ]
                },
                {
                    heading: "Your own marks",
                    body: [
                        "Map notes and points of interest are yours, stored in this browser. " +
                            "The game never receives them, which means you can write whatever " +
                            "you like in them."
                    ]
                }
            ]
        },

        {
            id: "entities",
            title: "People, items and context menus",
            group: "The world",
            summary: "Acting on things in the room without typing their names.",
            sections: [
                {
                    body: [
                        "Everything listed in a panel can be acted on. Clicking looks at it; " +
                            "the context menu offers whatever else applies.",
                        "Menu entries come from the game, so they are real commands this game " +
                            "actually has. Offering one does not make it legal -- it is sent " +
                            "like any other command and refused like any other command."
                    ]
                },
                {
                    heading: "Opening a menu",
                    keys: [
                        ["Right-click", "On any listed person, item or exit"],
                        ["Menu key", "With the entry focused"],
                        ["Shift+F10", "The same, on keyboards without a Menu key"],
                        ["Escape", "Close the menu, focus returns to the entry"]
                    ]
                },
                {
                    heading: "Your actions and the game's",
                    body: [
                        "Menus separate the two. Game actions send a command. Your own actions " +
                            "-- tagging someone as a friend, writing a note -- change data that " +
                            "never leaves this browser. They are kept visually distinct because " +
                            "they differ in kind, not just in origin."
                    ]
                }
            ]
        },

        {
            id: "character",
            title: "Resources, inventory, equipment and effects",
            group: "The world",
            summary: "The panels describing your character.",
            sections: [
                {
                    heading: "Resources",
                    body: [
                        "Whatever numbers this game exposes: health, fuel, sanity, favour. " +
                            "Aetos assigns no meaning to any of them and shows what the game " +
                            "declares.",
                        "The number is always shown, not only the bar, and a bar approaching " +
                            "a threshold says so in words as well as colour. When a threshold " +
                            "is crossed it is announced, so you do not have to be watching."
                    ]
                },
                {
                    heading: "Inventory",
                    body: [
                        "What you are carrying. This works on any Evennia game with no setup " +
                            "at all, because carrying things is something every game has."
                    ]
                },
                {
                    heading: "Equipment and target",
                    body: [
                        "Shown only if this game has them. Evennia does not model equipment " +
                            "slots or a current target, so a game that has not said it has them " +
                            "gets no panel -- rather than an empty paper doll implying a system " +
                            "that does not exist.",
                        "A target's bars use the identical rendering as your own, so learning " +
                            "to read one teaches you the other."
                    ]
                },
                {
                    heading: "Effects, and what a countdown means",
                    body: [
                        "Effects are anything temporarily true about you. A countdown is the " +
                            "client's estimate of what the server last said, and when it " +
                            "reaches zero the effect is shown as expiring rather than removed.",
                        "That is deliberate. Only the server knows when an effect actually " +
                            "ends, and a client that removed it on its own clock would show " +
                            "you as clean while the server still had you poisoned -- a lie at " +
                            "exactly the moment it matters most."
                    ]
                }
            ]
        },

        {
            id: "notes",
            title: "Notes, tags and relationships",
            group: "Your data",
            summary: "Private records about people, places and things.",
            sections: [
                {
                    body: [
                        "Write a note about anyone or anything, and tag people as friends, " +
                            "enemies or whatever categories you invent. Notes are searchable " +
                            "and attach to the thing they describe, so they surface when you " +
                            "meet that person again.",
                        "None of this reaches the game server. It is not a friends list the " +
                            "game knows about; it is your own memory, kept in your browser."
                    ]
                },
                {
                    heading: "Which means",
                    body: [
                        "Nobody else can see them -- not other players, not staff. Equally, " +
                            "they do not follow you to another computer unless you export and " +
                            "import them, and clearing your browser data clears them too. " +
                            "Export from the Privacy panel if they matter to you."
                    ]
                }
            ]
        },

        {
            id: "talk",
            title: "The picture and word board",
            group: "Your data",
            summary: "Build a sentence from words, check it, then send it.",
            sections: [
                {
                    body: [
                        "The Talk panel is a board of words in categories. Press one " +
                            "and it joins your sentence; press Preview and send and " +
                            "you see exactly what will be sent before anyone else " +
                            "does.",
                        "It sends ordinary game commands. \"I\", \"want\", " +
                            "\"help\" becomes `say i want help` -- the same thing " +
                            "you would have typed, judged by the game in the same " +
                            "way. A single direction is movement instead: pressing " +
                            "North on its own sends `north`."
                    ]
                },
                {
                    heading: "Everything works from the keyboard",
                    body: [
                        "Add a word, remove one, move it left or right, clear the " +
                            "whole sentence, preview, send. All buttons.",
                        "There is no drag-and-drop, deliberately. It would have been " +
                            "easier to build the mouse version first, and that is " +
                            "reliably how a keyboard path ends up as an afterthought " +
                            "nobody tests."
                    ]
                },
                {
                    heading: "You always see it before it is sent",
                    body: [
                        "The preview is not a politeness. If a word meant something " +
                            "slightly different from what you expected, that " +
                            "sentence would otherwise be said in public, under your " +
                            "name, without you seeing it.",
                        "So you get Send, Edit text and Cancel. Edit text matters as " +
                            "much as the other two -- you are the authority on what " +
                            "you meant, and the board is a keyboard, not a " +
                            "translator."
                    ]
                },
                {
                    heading: "About pictures",
                    body: [
                        "Aetos ships no symbol artwork, so every key shows its word " +
                            "until you install a symbol pack. Search the palette for " +
                            "\"Symbol packs\".",
                        "Free sets do exist. ARASAAC is a complete pictographic " +
                            "system covering the core words, but its licence forbids " +
                            "commercial use, so a client that games may charge money " +
                            "for cannot ship it -- you can install it yourself. " +
                            "Mulberry is freely licensed for any use, and Aetos " +
                            "includes a mapping for it, but it is a vocabulary set " +
                            "rather than a communication board: it has no picture for " +
                            "yes, no, stop, please, thank you or sorry.",
                        "Which set suits you depends on your game's licensing and on " +
                            "which symbols you already know. That is your choice, so " +
                            "Aetos does not make it for you."
                    ]
                },
                {
                    heading: "What a pack tells you before you rely on it",
                    body: [
                        "The Symbol packs panel lists exactly which words a pack has " +
                            "no picture for, so you find out there rather than by " +
                            "hitting a blank key in the middle of saying something.",
                        "A missing picture always falls back to the word, never to a " +
                            "similar-looking substitute -- a near-miss symbol is a " +
                            "different word, and you would have no way to know it " +
                            "happened.",
                        "It also tells you whether a pack is self-contained. A pack " +
                            "that loads its pictures from a website tells that site " +
                            "every time you use the board, which is a thing about you " +
                            "that you did not choose to share. Packs built with " +
                            "Aetos's own tool embed their pictures and send nothing."
                    ]
                },
                {
                    heading: "What this is, honestly",
                    body: [
                        "This is an AAC *architecture*, not reviewed AAC support, and " +
                            "Aetos does not claim otherwise anywhere.",
                        "Nobody familiar with picture-supported communication has " +
                            "reviewed the word choices, the categories, or how much " +
                            "work a sentence takes to build. Until somebody has, the " +
                            "honest description is that the extension point exists and " +
                            "the judgement has not been applied to it."
                    ]
                }
            ]
        },

        {
            id: "simplified",
            title: "The simplified layout",
            group: "Getting started",
            summary: "Four panels instead of a dozen, with nothing removed.",
            sections: [
                {
                    body: [
                        "Search the palette for \"Simplified layout\". You get the " +
                            "game text, who is here, the map, your character, and the " +
                            "Talk board -- with help where it always is.",
                        "Nothing is removed. Every feature is still in the " +
                            "palette, every command still works, and switching back " +
                            "restores what you had.",
                        "That distinction matters. A \"simple mode\" that quietly " +
                            "took features away would be making a decision about what " +
                            "you are capable of because you asked for a calmer screen. " +
                            "Those are not the same request."
                    ]
                },
                {
                    heading: "How it differs from focus mode",
                    body: [
                        "Focus mode hides everything except the game text and your " +
                            "input, and you turn it off again when you are done. This " +
                            "is a layout you might use permanently.",
                        "It also only adds panels your game actually has. A map panel " +
                            "on a game with no map would be one permanently empty " +
                            "box, which is worse than three panels."
                    ]
                }
            ]
        },

        {
            id: "themes",
            title: "Themes and contrast",
            group: "Your data",
            summary: "Change the colours, and find out whether you can still read them.",
            sections: [
                {
                    body: [
                        "Aetos ships a dark theme and a light one, and you can build " +
                            "your own. A theme changes colours and nothing else -- it " +
                            "cannot change spacing, type size, or anything about how " +
                            "the client behaves.",
                        "That limit is deliberate. A theme that could ship its own " +
                            "stylesheet could hide content, override the focus " +
                            "outline, or animate something you asked not to be " +
                            "animated. Colours only means a bad theme is hard to " +
                            "read, which you can see and undo, rather than broken in " +
                            "a way you cannot."
                    ]
                },
                {
                    heading: "Your accessibility settings always win",
                    body: [
                        "High contrast, reduced motion and minimal stimulation are " +
                            "applied on top of whatever theme is active, and they " +
                            "override it.",
                        "So picking a theme can never quietly undo an accommodation. " +
                            "If you have high contrast on and choose a soft pastel " +
                            "theme, you still have high contrast."
                    ]
                },
                {
                    heading: "Every theme is contrast-checked",
                    body: [
                        "When you save a theme, Aetos measures eleven colour pairs " +
                            "against the WCAG AA thresholds -- text on the " +
                            "background, secondary text on a panel, borders, the " +
                            "focus ring, and the success, warning and danger colours.",
                        "If any fail it tells you which, the ratio each one got, and " +
                            "what that pair is for. \"--aetos-text-muted is 2.10:1 " +
                            "against --aetos-panel\" on its own tells you that you " +
                            "are wrong without telling you what to change."
                    ]
                },
                {
                    heading: "It warns; it does not refuse",
                    body: [
                        "A theme that fails is still saved. If you want it, you can " +
                            "have it -- Aetos is not going to overrule you about your " +
                            "own eyes.",
                        "What it will not do is stay quiet. The warning also mentions " +
                            "that an exported theme reaches other people, who did not " +
                            "choose those colours and may not be able to read them.",
                        "The same check runs against Aetos's own themes as part of " +
                            "its tests. That found a real problem: the default panel " +
                            "borders had been at 1.37:1 since the client's fourth " +
                            "milestone, which meant that for anyone with reduced " +
                            "contrast sensitivity the panels had no visible edges at " +
                            "all. A palette chosen by eye passes for the person who " +
                            "chose it."
                    ]
                }
            ]
        },

        {
            id: "sound",
            title: "Sound and captions",
            group: "Your data",
            summary: "Volume you control, and text for everything you hear.",
            sections: [
                {
                    body: [
                        "If your game sends sound, the Sound panel lists every " +
                            "volume control -- overall, music, ambience, effects, " +
                            "interface and voice -- plus mute and a stop-everything " +
                            "button. All of them are ordinary sliders and buttons, so " +
                            "they work with a keyboard, a screen reader or a switch " +
                            "device without Aetos reinventing anything.",
                        "A game that sends no sound gets no panel, rather than six " +
                            "dead sliders."
                    ]
                },
                {
                    heading: "Everything is captioned",
                    body: [
                        "Every sound that carries information also appears as text, " +
                            "in the Sound panel and to your screen reader. That text " +
                            "is written *before* the sound is played, and it appears " +
                            "whether or not the sound plays at all -- muted, volume " +
                            "at zero, file missing, no speakers, browser blocking " +
                            "audio. Tying the text to a successful playback would " +
                            "mean the people who most need the text are the least " +
                            "likely to get it.",
                        "Sounds a game marks decorative -- a wind loop, a click -- " +
                            "play without a caption, because they carry nothing to " +
                            "caption."
                    ]
                },
                {
                    heading: "If a sound has no caption",
                    body: [
                        "You will see \"Uncaptioned effect audio\", or similar.",
                        "That is not Aetos failing. It is Aetos reporting that the " +
                            "game published a sound without saying what it means. " +
                            "Aetos cannot listen to a sound file and describe it, and " +
                            "it will not invent a caption -- a made-up description is " +
                            "confidently wrong to exactly the person who cannot check " +
                            "it. So it says what it knows and no more.",
                        "If you see these often, it is worth telling the game's staff."
                    ]
                },
                {
                    heading: "Nothing starts on its own",
                    body: [
                        "Browsers block audio until you have interacted with the " +
                            "page, and Aetos does not fight that. If sound is waiting " +
                            "on you, it says so once, in text, rather than failing " +
                            "silently.",
                        "Images are shown one at a time and stay until you hide them. " +
                            "Nothing disappears on a timer."
                    ]
                }
            ]
        },

        {
            id: "orientation",
            title: "Where am I, and how did I get here",
            group: "Your data",
            summary: "Pick up where you left off after an interruption.",
            sections: [
                {
                    body: [
                        "Press Ctrl+Shift+W, or search the palette for \"Where am I\". " +
                            "Aetos reads back where you are, the exits, who is present, " +
                            "your character's state, your target, and the last few " +
                            "commands you sent.",
                        "The game does not pause when you take a phone call, lose your " +
                            "place on a braille display, or simply look away. Scrollback " +
                            "answers \"what happened\"; this answers \"where am I\"."
                    ]
                },
                {
                    heading: "It reports facts, and only facts",
                    body: [
                        "Aetos will tell you that you sent \"look at Renn\". It will " +
                            "never tell you that you were investigating Renn.",
                        "That restraint is the point. A client that guessed at what you " +
                            "were doing would be confidently wrong at exactly the moment " +
                            "you were relying on it, and a wrong answer delivered with " +
                            "certainty costs you the time to discover it was wrong plus " +
                            "the trust you had in the feature."
                    ]
                },
                {
                    heading: "How I got here, and walking back",
                    body: [
                        "\"How I got here\" lists the rooms you have moved through. The " +
                            "trail is built from rooms the game actually put you in, not " +
                            "from movement you typed -- if you walked into a wall, that is " +
                            "not on the trail.",
                        "\"Walk back\" retraces it using ordinary movement commands, " +
                            "through the same queue a macro uses. A locked door stops it " +
                            "exactly where the game stops you. It also stops rather than " +
                            "guessing wherever a step has no clear reverse -- \"north\" " +
                            "reverses to \"south\", but \"enter the portal\" reverses to " +
                            "nothing anybody can be sure of."
                    ]
                },
                {
                    heading: "Reminders and tasks",
                    body: [
                        "Notes to yourself, kept in this browser. Pin one to keep it in " +
                            "view, attach one to a room so it comes back when you next " +
                            "walk in, or hold one until your next session.",
                        "Aetos never creates one. It does not notice you have not visited " +
                            "somewhere lately and it does not build a checklist out of " +
                            "your behaviour. A memory aid that edits itself is a memory " +
                            "aid you cannot trust.",
                        "A room reminder surfaces once per visit, not once per second."
                    ]
                },
                {
                    heading: "Finding things",
                    body: [
                        "The command palette searches your notes, your reminders and " +
                            "what has been said, alongside the client's own commands. You " +
                            "do not have to remember which panel something is in before " +
                            "you can look for it.",
                        "A result from the history jumps to that moment in Review Mode, " +
                            "so it is reachable even if a display rule has since hidden " +
                            "the line."
                    ]
                },
                {
                    heading: "Focus mode and quiet mode",
                    body: [
                        "Focus mode hides everything except the game text and your " +
                            "input. Quiet mode stops routine announcements.",
                        "They are separate on purpose: wanting a calmer screen and " +
                            "wanting fewer interruptions are different needs. Quiet mode " +
                            "is about interruption, not information -- anything important " +
                            "still gets through, nothing leaves the transcript, and if you " +
                            "ask a direct question you still get an answer.",
                        "Nothing the game sends turns either of them on or off. Only you " +
                            "do."
                    ]
                }
            ]
        },

        {
            id: "privacy",
            title: "Privacy and your data",
            group: "Your data",
            summary: "What is stored, where, and how to take it or delete it.",
            sections: [
                {
                    body: [
                        "Aetos stores your settings in this browser and sends none of them to " +
                            "the game server. That is a design constraint, not a preference: " +
                            "the client is built so that there is no code path that could send " +
                            "them.",
                        "\"Privacy and local data\" in the palette lists everything currently " +
                            "stored, counted from storage rather than assumed, and tells you " +
                            "whether this browser is storing anything at all -- in a private " +
                            "window it is not, and nothing will survive the session."
                    ]
                },
                {
                    heading: "What is stored here",
                    body: [
                        "Layouts and workspaces, macros, aliases, triggers, timers, scripts " +
                            "and their variables, relationship tags, notes, map notes and " +
                            "points of interest, themes, keybindings and preferences."
                    ]
                },
                {
                    heading: "Taking it with you",
                    body: [
                        "Export writes all of it to a single JSON file you can read, edit and " +
                            "import on another machine. Import tells you what it accepted and " +
                            "what it refused, because an import that silently dropped half a " +
                            "file would be worse than one that failed outright."
                    ]
                },
                {
                    heading: "Deleting it",
                    body: [
                        "\"Clear all Aetos data\" removes everything, after confirming exactly " +
                            "how many items will go. It does not touch your game account, and " +
                            "it does not touch anything belonging to other software on this " +
                            "browser."
                    ]
                }
            ]
        },

        {
            id: "accessibility",
            title: "Accessibility",
            group: "Your data",
            summary: "Keyboard operation, screen readers and announcements.",
            sections: [
                {
                    heading: "Where the options are",
                    body: [
                        "The Accessibility button in the bar at the top opens a panel of "
                            + "options you can turn on and off individually -- contrast, text "
                            + "size, motion, how much is announced, a calmer screen, "
                            + "orientation help, a picture and word board, and more. Ctrl+Shift+A "
                            + "opens the same panel.",
                        "There is no bundle to accept or refuse. Each one is separate, and "
                            + "all of them are also in Settings if that is where you looked "
                            + "first.",
                        "The switch at the top right moves between two modes. Standard "
                            + "mode is the client as it comes; accessible mode applies what "
                            + "you chose. Switching back to standard stops them applying and "
                            + "keeps every one of them, so you can look at the standard "
                            + "interface and come straight back with the same keystroke.",
                        "The Options button beside it opens the settings, and works in both "
                            + "modes. Standard mode offers text size, sound, gestures and "
                            + "orientation help; accessible mode adds contrast, motion, "
                            + "announcements and layout to that list.",
                        "Text size is in both on purpose. Being able to make the text bigger "
                            + "is not something you should have to switch modes for, and it "
                            + "stays where you put it when you do. Larger text and Smaller "
                            + "text are also in the command palette, so you never have to "
                            + "read a settings panel to fix the size of the text."
                    ],
                    keys: [
                        ["Ctrl+Shift+A", "Show or hide the accessibility options"]
                    ]
                },
                {
                    heading: "What is always on",
                    body: [
                        "Everything in Aetos is reachable from the keyboard. Nothing requires " +
                            "a mouse, and nothing requires seeing a colour: where colour " +
                            "carries meaning, the same meaning is written in the text.",
                        "Dialogs trap focus while open and return it where it came from on " +
                            "close, so you never have to tab through the whole interface to " +
                            "find your place again."
                    ]
                },
                {
                    heading: "Announcements",
                    body: [
                        "Important changes are announced without stealing focus: a crossed " +
                            "resource threshold, an effect gained or ended, a target changed.",
                        "Countdowns are deliberately not announced. A live region updating " +
                            "every second would flood a screen reader with the one piece of " +
                            "information you can read whenever you choose to."
                    ]
                },
                {
                    heading: "The map without a map",
                    body: [
                        "The map's written description is generated from the same data as the " +
                            "picture, not written separately, so the two cannot drift apart."
                    ]
                }
            ]
        },

        {
            id: "history",
            title: "Finding something that already happened",
            group: "Basics",
            summary: "Search everything the game has said, and read around it.",
            sections: [
                {
                    body: [
                        "Everything the game sends you is kept for this session, whether or " +
                            "not it is still on screen. The console keeps the last few " +
                            "thousand lines; the record behind it keeps more, and keeps the " +
                            "ones the console was told to hide.",
                        "That record is what the History panel searches. It is stored in this " +
                            "browser and nowhere else -- the game is not asked, and is not " +
                            "told what you searched for."
                    ]
                },
                {
                    heading: "Review Mode",
                    body: [
                        "Opening a result puts you in Review Mode, which pins the console to " +
                            "that moment so you can read around it. New output keeps arriving " +
                            "and is not lost; you are simply not being dragged to the bottom " +
                            "while you read.",
                        "Leave Review Mode and the console returns to following the game. " +
                            "There is no way to be left in it by accident: it says so on " +
                            "screen and announces itself when it starts and stops."
                    ],
                    keys: [
                        ["Escape", "Leave Review Mode and follow the game again"]
                    ]
                },
                {
                    heading: "Filtering",
                    body: [
                        "Results can be narrowed to one channel -- say, tells, or combat -- " +
                            "using the buttons above the list. The channel is written as a " +
                            "word on every entry rather than shown as a colour, so the list " +
                            "reads the same however you see it."
                    ]
                }
            ]
        },

        {
            id: "groups",
            title: "Turning sets of automation on and off",
            group: "Automation",
            summary: "Switch a whole set of macros, aliases and triggers at once.",
            sections: [
                {
                    body: [
                        "Once you have more than a few aliases and triggers, most of them are " +
                            "wrong most of the time. A trigger that is useful in a fight is a " +
                            "nuisance in a shop.",
                        "A group is a named set of your own automation that you can switch on " +
                            "and off together. Anything can belong to more than one group, and " +
                            "anything belonging to no group is always active."
                    ]
                },
                {
                    heading: "Where they are",
                    body: [
                        "Settings, under Automation groups. Each group shows how many things " +
                            "belong to it and whether it is currently on, in words rather than " +
                            "as a colour."
                    ]
                },
                {
                    heading: "What switching off actually does",
                    body: [
                        "A group that is off stops its members from firing. It does not delete " +
                            "them, does not edit them, and does not change anything you wrote. " +
                            "Turning it back on returns everything exactly as it was.",
                        "Groups are yours and live in this browser. The game does not know they " +
                            "exist and is not told which ones are on."
                    ]
                }
            ]
        },

        {
            id: "install",
            title: "Installing the client, and what happens offline",
            group: "Basics",
            summary: "Keep the client on your device, and what a lost connection looks like.",
            sections: [
                {
                    body: [
                        "Aetos can be installed as an application on most desktop and mobile " +
                            "browsers, which gives it its own window and its own icon. It is " +
                            "the same client either way -- installing changes where it opens, " +
                            "not what it does.",
                        "Look for your browser's install control, or the Install option in the " +
                            "command palette when your browser offers one. Some browsers do " +
                            "not, in which case the client works exactly as before."
                    ]
                },
                {
                    heading: "Offline",
                    body: [
                        "Once installed, the client itself loads without the network. The " +
                            "game itself does not. You will get the interface and a clear message " +
                            "that it is not connected, rather than a browser error page -- " +
                            "which is worth having on a train, but is not a way to play.",
                        "Nothing the game sends is ever stored for offline use. What is kept " +
                            "is the client's own files, and that is deliberate: a cache of " +
                            "game text would be a copy of your session sitting on the device."
                    ]
                },
                {
                    heading: "When the connection drops",
                    body: [
                        "Everything on screen dims and says so. What the panels show is the " +
                            "last state the game sent, which was true when it arrived and may " +
                            "not be true now.",
                        "Commands typed while disconnected are not sent and not saved for " +
                            "later. You are told each time. Nothing is queued up to fire when " +
                            "the connection returns, because by then you may be somewhere else " +
                            "entirely and the command would be a decision about a situation " +
                            "that no longer exists."
                    ]
                },
                {
                    heading: "Updates",
                    body: [
                        "When the game updates the client, you are told and nothing changes " +
                            "until you choose to apply it. An update that reloaded the page on " +
                            "its own would do it in the middle of somebody's fight."
                    ]
                }
            ]
        },

        {
            id: "developers",
            title: "For game developers",
            group: "Running a game",
            summary: "Making Aetos show your game's systems.",
            sections: [
                {
                    body: [
                        "Aetos knows nothing about your game, and never guesses during play. " +
                            "There is no genre concept anywhere in the client -- no health, " +
                            "no combat, no inventory slot names. You tell it where your data " +
                            "is, or you supply code that produces it.",
                        "Nothing below grants authority. Every button the client renders sends " +
                            "an ordinary command, subject to your locks and rules exactly as " +
                            "if the player had typed it."
                    ]
                },
                {
                    heading: "Three levels. Most games never need the third.",
                    example:
                        "Level 0   nothing            a stock game already works\n" +
                        "Level 1   AETOS_BINDINGS     \"my health is at db.hp\"\n" +
                        "Level 2   custom provider    when a value is calculated"
                },
                {
                    heading: "Level 1 -- tell Aetos where your data is  (planned)",
                    body: [
                        "A binding says where a value lives. No class, no import, and " +
                            "normally no feature flag -- declaring a binding is enough to turn " +
                            "the matching interface on."
                    ],
                    example:
                        "# server/conf/settings.py\n" +
                        "AETOS_BINDINGS = {\n" +
                        '    "resources": {\n' +
                        '        "health": {"label": "Health",\n' +
                        '                   "value": "db.hp",\n' +
                        '                   "maximum": "db.hp_max"},\n' +
                        "    },\n" +
                        '    "target": {"object": "db.current_target"},\n' +
                        "}"
                },
                {
                    heading: "Not sure where your data is? Run Discovery.",
                    body: [
                        "A development-time tool that inspects your own game -- a " +
                            "representative character, your typeclasses, your command set -- " +
                            "and suggests the bindings, with its evidence and how confident it " +
                            "is beside each one.",
                        "evennia aetos discover prints the suggestions in one go. " +
                            "evennia aetos setup walks them one at a time and reads each value " +
                            "off a live character, so you see the number before you keep it, " +
                            "lets you correct anything, and writes what you accept to " +
                            "aetos-discovery/ for you to paste in.",
                        "It never edits your game, never runs your code, and is not reachable " +
                            "by players. And when it cannot tell two candidates apart it says " +
                            "so rather than picking one."
                    ],
                    example:
                        "evennia aetos setup --character #12\n\n" +
                        "Possible resource found\n" +
                        "-----------------------\n" +
                        "Suggested name:  Health\n" +
                        "Value:           db.hp\n" +
                        "Maximum:         db.hp_max\n" +
                        "Test values:     82 / 100\n\n" +
                        "Evidence:\n" +
                        "  - hp and hp_max are named like a value and its ceiling\n" +
                        "  - both are numbers on the characters read\n\n" +
                        "Confidence: HIGH\n\n" +
                        "Use this integration?  [Y]es [E]dit [N]o [?]explain [Q]uit"
                },
                {
                    heading: "Where bindings stop, and why",
                    body: [
                        "Bindings describe where data IS. Providers describe how it is " +
                            "CALCULATED. So db.hp is a binding, and " +
                            "stats.get(\"health\").current is not -- it is a method call, and " +
                            "bindings deliberately do not allow those.",
                        "That line is kept sharp on purpose. A binding language that grew " +
                            "until it could express calculations would be a programming " +
                            "language with no debugger, no error messages worth reading, and " +
                            "nowhere to put a breakpoint."
                    ]
                },
                {
                    heading: "Level 2 -- exposing resources with a provider",
                    example:
                        "# world/aetos.py\n" +
                        "from evennia.contrib.base_systems.aetos_webclient.providers.base import (\n" +
                        "    AetosResourceProvider,\n" +
                        ")\n\n\n" +
                        "class MyResources(AetosResourceProvider):\n" +
                        "    def get_resources(self, character):\n" +
                        "        return [\n" +
                        "            {\n" +
                        '                "id": "health",\n' +
                        '                "label": "Health",\n' +
                        '                "value": character.db.hp or 0,\n' +
                        '                "maximum": character.db.hp_max or 100,\n' +
                        '                "thresholds": [\n' +
                        '                    {"at": 0.25, "level": "warning",\n' +
                        '                     "message": "Health is low."},\n' +
                        "                ],\n" +
                        "            }\n" +
                        "        ]"
                },
                {
                    heading: "Turning a provider on",
                    example:
                        "# server/conf/settings.py\n" +
                        'AETOS_PROVIDERS = {"resources": "world.aetos.MyResources"}\n' +
                        'AETOS_FEATURES = {"resources": True}\n\n' +
                        "# Policy: what players may automate. Descriptive, never permissive.\n" +
                        "AETOS_AUTOMATION = {\n" +
                        '    "macros": True,\n' +
                        '    "aliases": True,\n' +
                        '    "triggers": True,\n' +
                        '    "timers": False,\n' +
                        '    "scripting": False,\n' +
                        "}"
                },
                {
                    heading: "The slots",
                    example:
                        "resources   what your game measures     (no default -- opt in)\n" +
                        "entities    what is in the room         (works out of the box)\n" +
                        "actions     context-menu commands       (look/get/drop by default)\n" +
                        "map         the local room graph        (walks visible exits)\n" +
                        "inventory   what a character carries    (works out of the box)\n" +
                        "equipment   equipped items by slot      (no default -- opt in)\n" +
                        "target      the current target          (no default -- opt in)\n" +
                        "effects     temporary conditions        (no default -- opt in)"
                },
                {
                    heading: "Two rules worth knowing",
                    body: [
                        "A misconfigured provider fails loudly at startup, naming the setting, " +
                            "the slot and the import that failed. A provider that raises at " +
                            "runtime is contained instead: it costs its own widget and logs a " +
                            "traceback, because by then a player is connected and losing one " +
                            "panel beats losing the session.",
                        "Aetos never stores player configuration on your server. There are no " +
                            "models and no migrations, and installing it adds no rows to your " +
                            "database."
                    ]
                },
                {
                    heading: "Real-time updates",
                    example:
                        "# Optional. Without it, the client asks for a sync after each\n" +
                        "# command, which needs no cooperation from your game at all.\n" +
                        "from evennia.contrib.base_systems.aetos_webclient import state\n\n\n" +
                        "class Character(DefaultCharacter):\n" +
                        "    def at_post_move(self, source_location, **kwargs):\n" +
                        "        super().at_post_move(source_location, **kwargs)\n" +
                        "        for session in self.sessions.all():\n" +
                        "            state.push_sync(session, self)"
                }
            ]
        }
    ];

    /* ------------------------------------------------------------------
     * Search
     * ------------------------------------------------------------------ */

    function topicText(topic) {
        var parts = [topic.title, topic.summary, topic.group];
        (topic.sections || []).forEach(function (section) {
            if (section.heading) {
                parts.push(section.heading);
            }
            (section.body || []).forEach(function (line) { parts.push(line); });
            if (section.example) {
                parts.push(section.example);
            }
            (section.keys || []).forEach(function (row) {
                parts.push(row[0]);
                parts.push(row[1]);
            });
        });
        return parts.join(" ").toLowerCase();
    }

    function matches(topic, query) {
        if (!query) {
            return true;
        }
        return topicText(topic).indexOf(query.toLowerCase()) !== -1;
    }

    /* ------------------------------------------------------------------
     * Rendering
     * ------------------------------------------------------------------ */

    function renderSection(section) {
        var block = document.createElement("section");
        block.className = "aetos-help__section";

        if (section.heading) {
            var heading = document.createElement("h3");
            heading.className = "aetos-help__heading";
            heading.textContent = section.heading;
            block.appendChild(heading);
        }

        (section.body || []).forEach(function (line) {
            var paragraph = document.createElement("p");
            // Always textContent. Help text is authored here rather than
            // supplied by the game, but rendering it as markup anyway would
            // leave a hole for the day someone makes it configurable.
            paragraph.textContent = line;
            block.appendChild(paragraph);
        });

        if (section.example) {
            var pre = document.createElement("pre");
            pre.className = "aetos-help__example";
            // Examples are meant to be copied, so they are selectable text in a
            // real <pre> rather than an image or a styled div.
            pre.textContent = section.example;

            /*
             * FOCUSABLE, BECAUSE IT SCROLLS.
             *
             * An example is `white-space: pre` and scrolls sideways rather than
             * wrapping, and that is the right call for this content: several of
             * them are column-aligned tables, and wrapping "resources   what
             * your game measures" would destroy the alignment that makes it
             * readable. WCAG 1.4.10 allows exactly that -- content requiring a
             * two-dimensional layout.
             *
             * What it does not allow is a region you can only scroll with a
             * mouse. axe found one long example at an 800px viewport
             * (`scrollable-region-focusable`, serious): the end of the line was
             * unreachable from the keyboard, and at a larger text size that is
             * true of most of them.
             *
             * Every example is focusable, not only the ones that currently
             * overflow. Whether one overflows depends on the window width and
             * the player's text size and changes under both, so a conditional
             * `tabindex` would be a control that is sometimes there -- and this
             * project has been caught more than once by a rule that quietly
             * became a no-op. The cost is one tab stop per example, on content a
             * keyboard user wants to reach anyway in order to copy it.
             */
            pre.tabIndex = 0;
            /*
             * `role="group"` rather than a bare label: ARIA prohibits naming an
             * element with the generic role, so `aria-label` on a plain <pre>
             * would be dropped by some screen readers and flagged by axe as a
             * prohibited attribute -- trading one violation for another.
             *
             * `group` over `region` because `region` is a landmark, and a help
             * article with eight examples would add eight landmarks to a
             * document where they mean nothing.
             */
            pre.setAttribute("role", "group");
            pre.setAttribute(
                "aria-label",
                section.heading ? "Example: " + section.heading : "Example"
            );
            block.appendChild(pre);
        }

        if (section.keys) {
            var table = document.createElement("dl");
            table.className = "aetos-help__keys";
            section.keys.forEach(function (row) {
                var key = document.createElement("dt");
                var keyCode = document.createElement("kbd");
                keyCode.textContent = row[0];
                key.appendChild(keyCode);
                var description = document.createElement("dd");
                description.textContent = row[1];
                table.appendChild(key);
                table.appendChild(description);
            });
            block.appendChild(table);
        }

        return block;
    }

    function renderTopic(topic) {
        var article = document.createElement("article");
        article.className = "aetos-help__article";
        /*
         * tabindex="0", not "-1".
         *
         * Two requirements meet here. Choosing a topic moves focus to the
         * article, so a screen-reader user lands on the content rather than
         * hunting for where it appeared -- "-1" would satisfy that alone.
         *
         * But the article sits in a scrolling container, and a region that
         * scrolls must be reachable by Tab or a keyboard user cannot scroll it
         * at all: arrow keys scroll whatever has focus, and "-1" keeps it out
         * of the tab order. Found by axe as `scrollable-region-focusable`,
         * which is precisely the class of defect that is invisible to anyone
         * testing with a mouse.
         */
        article.setAttribute("tabindex", "0");
        article.setAttribute("aria-label", topic.title);

        var title = document.createElement("h2");
        title.className = "aetos-help__title";
        title.textContent = topic.title;
        article.appendChild(title);

        var summary = document.createElement("p");
        summary.className = "aetos-help__summary";
        summary.textContent = topic.summary;
        article.appendChild(summary);

        (topic.sections || []).forEach(function (section) {
            article.appendChild(renderSection(section));
        });

        return article;
    }

    /* ------------------------------------------------------------------
     * The overlay
     * ------------------------------------------------------------------ */

    function createHelp(services) {
        var isAllowed = services.isAllowed || function () { return true; };
        var announce = services.announce || function () {};
        var open = null;

        /*
         * Only topics for features this game permits.
         *
         * Documenting scripting on a game that forbids it sends the player
         * looking for a button that is not there, which is a worse outcome than
         * no documentation at all (blueprint section 32).
         */
        function availableTopics() {
            return TOPICS.filter(function (topic) {
                return !topic.requires || isAllowed(topic.requires);
            });
        }

        function close() {
            if (!open) {
                return false;
            }
            var current = open;
            open = null;
            if (current.overlay.parentNode) {
                current.overlay.parentNode.removeChild(current.overlay);
            }
            document.removeEventListener("keydown", current.keyHandler, true);
            if (current.opener && document.contains(current.opener)) {
                current.opener.focus();
            }
            return true;
        }

        function openHelp(topicId) {
            close();

            var opener = document.activeElement;
            var topics = availableTopics();
            var selected = topicId || topics[0].id;

            var overlay = document.createElement("div");
            overlay.className = "aetos-help__overlay";

            var panel = document.createElement("div");
            panel.className = "aetos-help";
            panel.setAttribute("role", "dialog");
            panel.setAttribute("aria-modal", "true");
            panel.setAttribute("aria-label", "Aetos help");

            /* --- header ------------------------------------------------- */

            var header = document.createElement("div");
            header.className = "aetos-help__header";

            var title = document.createElement("h1");
            title.className = "aetos-help__brand";
            title.textContent = "Aetos help";
            header.appendChild(title);

            var searchLabel = document.createElement("label");
            searchLabel.className = "aetos-visually-hidden";
            searchLabel.setAttribute("for", "aetos-help-search");
            searchLabel.textContent = "Search help";

            var search = document.createElement("input");
            search.type = "text";
            search.id = "aetos-help-search";
            search.className = "aetos-input aetos-help__search";
            search.placeholder = "Search help";

            var closeButton = document.createElement("button");
            closeButton.type = "button";
            closeButton.className = "aetos-list__button";
            closeButton.textContent = "Close";
            closeButton.addEventListener("click", function () { close(); });

            header.appendChild(searchLabel);
            header.appendChild(search);
            header.appendChild(closeButton);
            panel.appendChild(header);

            /* --- body --------------------------------------------------- */

            var body = document.createElement("div");
            body.className = "aetos-help__body";

            var nav = document.createElement("nav");
            nav.className = "aetos-help__nav";
            nav.setAttribute("aria-label", "Help topics");

            var content = document.createElement("div");
            content.className = "aetos-help__content";

            body.appendChild(nav);
            body.appendChild(content);
            panel.appendChild(body);

            function show(id, moveFocus) {
                selected = id;
                var topic = topics.filter(function (t) { return t.id === id; })[0];
                content.textContent = "";
                if (!topic) {
                    return;
                }
                var article = renderTopic(topic);
                content.appendChild(article);
                content.scrollTop = 0;
                nav.querySelectorAll("[data-aetos-topic]").forEach(function (button) {
                    var active = button.getAttribute("data-aetos-topic") === id;
                    button.setAttribute("aria-current", active ? "page" : "false");
                });
                if (moveFocus) {
                    article.focus();
                }
            }

            function buildNav() {
                nav.textContent = "";
                var query = search.value.trim();
                var shown = topics.filter(function (topic) { return matches(topic, query); });

                if (!shown.length) {
                    var none = document.createElement("p");
                    none.className = "aetos-help__none";
                    none.textContent = "Nothing matches " + query + ".";
                    nav.appendChild(none);
                    content.textContent = "";
                    return;
                }

                var group = null;
                var list = null;
                shown.forEach(function (topic) {
                    if (topic.group !== group) {
                        group = topic.group;
                        var heading = document.createElement("h2");
                        heading.className = "aetos-help__group";
                        heading.textContent = group;
                        nav.appendChild(heading);
                        list = document.createElement("ul");
                        list.className = "aetos-list";
                        nav.appendChild(list);
                    }
                    var row = document.createElement("li");
                    var button = document.createElement("button");
                    button.type = "button";
                    button.className = "aetos-list__button";
                    button.textContent = topic.title;
                    button.setAttribute("data-aetos-topic", topic.id);
                    button.addEventListener("click", function () { show(topic.id, true); });
                    row.appendChild(button);
                    list.appendChild(row);
                });

                // Searching narrows the topics; showing the first match saves a
                // second interaction to see whether it was what you wanted.
                var stillShown = shown.filter(function (t) { return t.id === selected; }).length;
                show(stillShown ? selected : shown[0].id, false);
            }

            search.addEventListener("input", buildNav);

            overlay.appendChild(panel);
            document.body.appendChild(overlay);
            buildNav();

            function keyHandler(event) {
                if (event.key === "Escape") {
                    event.preventDefault();
                    close();
                    return;
                }
                if (event.key !== "Tab") {
                    return;
                }
                // Focus stays inside while the overlay is open. Without this,
                // Tab walks into the interface behind it, where a screen-reader
                // user can operate controls they cannot see.
                /*
                 * `[tabindex='0']` is in the list because the examples are.
                 *
                 * The selector named the three kinds of focusable element help
                 * happened to contain, which is a list that goes stale the
                 * moment anything is added -- and it just did. An example that
                 * sits after the last button in the DOM would have been skipped
                 * entirely: Tab from that button matched `last` and wrapped
                 * straight back to `first`, past the thing it should have
                 * reached next.
                 *
                 * A focus trap whose idea of "focusable" is narrower than the
                 * browser's does not trap focus, it loses it.
                 */
                var focusable = Array.prototype.slice.call(
                    panel.querySelectorAll(
                        "button, input, [tabindex='-1'], [tabindex='0']"
                    )
                ).filter(function (element) { return element.offsetParent !== null; });
                if (!focusable.length) {
                    return;
                }
                var first = focusable[0];
                var last = focusable[focusable.length - 1];
                if (event.shiftKey && document.activeElement === first) {
                    event.preventDefault();
                    last.focus();
                } else if (!event.shiftKey && document.activeElement === last) {
                    event.preventDefault();
                    first.focus();
                }
            }

            document.addEventListener("keydown", keyHandler, true);
            open = { overlay: overlay, keyHandler: keyHandler, opener: opener };

            search.focus();
            announce("Help open. " + topics.length + " topics.");
            return true;
        }

        /*
         * Toggle: open, or close if already open.
         *
         * F1 is registered with AetosShortcutManager rather than bound here, so
         * it is listed, rebindable and disableable alongside everything else
         * (A.23). F1 is one of the few keys safe to bind bare -- screen readers
         * claim single *characters* for structural navigation, not function
         * keys.
         */
        function toggle() {
            if (!close()) {
                return openHelp(null);
            }
            return false;
        }

        return {
            open: openHelp,
            close: close,
            toggle: toggle,
            topics: availableTopics,
            isOpen: function () { return !!open; }
        };
    }

    window.AetosHelp = {
        create: createHelp,
        TOPICS: TOPICS,
        matches: matches
    };

})(window, document);
