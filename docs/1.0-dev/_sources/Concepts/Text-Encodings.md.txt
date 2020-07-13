# Text Encodings


Evennia is a text-based game server. This makes it important to understand how
it actually deals with data in the form of text.

Text *byte encodings* describe how a string of text is actually stored in the
computer - that is, the particular sequence of bytes used to represent the
letters of your particular alphabet. A common encoding used in English-speaking
languages is the *ASCII* encoding. This describes the letters in the English
alphabet (Aa-Zz) as well as a bunch of special characters. For describing other
character sets (such as that of other languages with other letters than
    English), sets with names such as *Latin-1*, *ISO-8859-3* and *ARMSCII-8*
are used. There are hundreds of different byte encodings in use around the
world.

A string of letters in a byte encoding is represented with the `bytes` type.
In contrast to the byte encoding is the *unicode representation*. In Python
this is the `str` type. The unicode is an internationally agreed-upon table
describing essentially all available letters you could ever want to print.
Everything from English to Chinese alphabets and all in between. So what
Evennia (as well as Python and Django) does is to store everything in Unicode
internally, but then converts the data to one of the encodings whenever
outputting data to the user.

An easy memory aid is that `bytes` are what are sent over the network wire. At
all other times, `str` (unicode) is used. This means that we must convert
between the two at the points where we send/receive network data.

The problem is that when receiving a string of bytes over the network it's
impossible for Evennia to guess which encoding was used - it's just a bunch of
bytes! Evennia must know the encoding in order to convert back and from the
correct unicode representation.

## How to customize encodings

As long as you stick to the standard ASCII character set (which means the
normal English characters, basically) you should not have to worry much
about this section.

If you want to build your game in another language however, or expect your
users to want to use special characters not in ASCII, you need to consider
which encodings you want to support.

As mentioned, there are many, many byte-encodings used around the world. It
should be clear at this point that Evennia can't guess but has to assume or
somehow be told which encoding you want to use to communicate with the server.
Basically the encoding used by your client must be the same encoding used by
the server. This can be customized in two complementary ways.

1. Point users to the default `@encoding` command or the `@options` command.
   This allows them to themselves set which encoding they (and their client of
   choice) uses.  Whereas data will remain stored as unicode strings internally in
   Evennia, all data received from and sent to this particular player will be
   converted to the given format before transmitting.
1. As a back-up, in case the user-set encoding translation is erroneous or
   fails in some other way, Evennia will fall back to trying with the names
   defined in the settings variable `ENCODINGS`. This is a list of encoding
   names Evennia will try, in order, before giving up and giving an encoding
   error message.

Note that having to try several different encodings every input/output adds
unneccesary overhead. Try to guess the most common encodings you players will
use and make sure these are tried first. The International *UTF-8* encoding is
what Evennia assumes by default (and also what Python/Django use normally). See
the Wikipedia article [here](http://en.wikipedia.org/wiki/Text_encodings) for more help.