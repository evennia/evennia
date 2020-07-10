# Batch Processors


Building a game world is a lot of work, especially when starting out. Rooms should be created,
descriptions have to be written, objects must be detailed and placed in their proper places. In many
traditional MUD setups you had to do all this online, line by line, over a telnet session.

Evennia already moves away from much of this by shifting the main coding work to external Python
modules. But also building would be helped if one could do some or all of it externally. Enter
Evennia's *batch processors* (there are two of them). The processors allows you, as a game admin, to
build your game completely offline in normal text files (*batch files*) that the processors
understands. Then, when you are ready, you use the processors to read it all into Evennia (and into
the database) in one go.

You can of course still build completely online should you want to - this is certainly the easiest
way to go when learning and for small build projects. But for major building work, the advantages of
using the batch-processors are many:
- It's hard to compete with the comfort of a modern desktop text editor; Compared to a traditional
MUD line input, you can get much better overview and many more features. Also, accidentally pressing
Return won't immediately commit things to the database.
- You might run external spell checkers on your batch files. In the case of one of the batch-
processors (the one that deals with Python code), you could also run external debuggers and code
analyzers on your file to catch problems before feeding it to Evennia.
- The batch files (as long as you keep them) are records of your work. They make a natural starting
point for quickly re-building your world should you ever decide to start over.
- If you are an Evennia developer, using a batch file is a fast way to setup a test-game after
having reset the database.
- The batch files might come in useful should you ever decide to distribute all or part of your
world to others.


There are two batch processors, the Batch-*command* processor and the Batch-*code* processor. The
first one is the simpler of the two. It doesn't require any programming knowledge - you basically
just list in-game commands in a text file. The code-processor on the other hand is much more
powerful but also more complex - it lets you use Evennia's API to code your world in full-fledged
Python code.

- The [Batch Command Processor](./Batch-Command-Processor)
- The [Batch Code Processor](./Batch-Code-Processor)

If you plan to use international characters in your batchfiles you are wise to read about *file
encodings* below.

## A note on File Encodings

As mentioned, both the processors take text files as input and then proceed to process them. As long
as you stick to the standard [ASCII](http://en.wikipedia.org/wiki/Ascii) character set (which means
the normal English characters, basically) you should not have to worry much about this section.

Many languages however use characters outside the simple `ASCII` table. Common examples are various
apostrophes and umlauts but also completely different symbols like those of the greek or cyrillic
alphabets.

First, we should make it clear that Evennia itself handles international characters just fine. It
(and Django) uses [unicode](http://en.wikipedia.org/wiki/Unicode) strings internally.

The problem is that when reading a text file like the batchfile, we need to know how to decode the
byte-data stored therein to universal unicode. That means we need an *encoding* (a mapping) for how
the file stores its data. There are many, many byte-encodings used around the world, with opaque
names such as `Latin-1`, `ISO-8859-3` or `ARMSCII-8` to pick just a few examples. Problem is that
it's practially impossible to determine which encoding was used to save a file just by looking at it
(it's just a bunch of bytes!). You have to *know*.

With this little introduction it should be clear that Evennia can't guess but has to *assume* an
encoding when trying to load a batchfile. The text editor and Evennia must speak the same "language"
so to speak. Evennia will by default first try the international `UTF-8` encoding, but you can have
Evennia try any sequence of different encodings by customizing the `ENCODINGS` list in your settings
file. Evennia will use the first encoding in the list that do not raise any errors. Only if none
work will the server give up and return an error message.

You can often change the text editor encoding (this depends on your editor though), otherwise you
need to add the editor's encoding to Evennia's `ENCODINGS` list. If you are unsure, write a test
file with lots of non-ASCII letters in the editor of your choice, then import to make sure it works
as it should.

More help with encodings can be found in the entry [Text Encodings](../Concept/Text-Encodings) and also in the
Wikipedia article [here](http://en.wikipedia.org/wiki/Text_encodings).

**A footnote for the batch-code processor**: Just because *Evennia* can parse your file and your
fancy special characters, doesn't mean that *Python* allows their use. Python syntax only allows
international characters inside *strings*. In all other source code only `ASCII` set characters are
allowed.