rtclient protocol
=================

*Note: Most functionality of a webcliebnt implementation is already
added to trunk as of Nov 2010. That implementation does however not use
a custom protocol as suggested below. Rather it parses telnet-formatted
ansi text and converts it to html. Custom client operations (such as
opening windows or other features not relevant to telnet or other
protocols) should instead eb handled by a second "data" object being
passed to the server through the msg() method.*

rtclient is an extended and bastardized telnet protocol that processes
html and javascript embedded in the telnet session.

rtclient is implemented by the Teltola client, a web-based html/js
telnet client that is being integrated with Evennia and is written in
twisted/python.

There are two principle aspects to the rtclient protocol, mode control
and buffering.

Modes
=====

Unencoded Mode
--------------

All output is buffered until ascii char 10, 13, or 255 is encountered or
the mode changes or no output has been added to the buffer in the last
1/10th second and the buffer is not blank. When this occurs, the client
interprets the entire buffer as plain text and flushes the buffer.

HTML Mode
---------

All output is buffered. When the mode changes, the client then parses
the entire buffer as HTML.

Javascript Mode
---------------

All output is buffered. When the mode changes, the client then parses
the entire buffer as Javascript.

Sample Sessions
===============

# start html mode, send html, force buffer flush

::

    session.msg(chr(240) + "<h1>Test</h1>" + chr(242) + chr(244))

# same as above, but realize that msg sends end-of-line # automatically
thus sending the buffer via AUTO\_CHNK

::

    session.msg(chr(240) + "<h1>Test</h1>" + chr(242))

# more elaborate example sending javascript, html, and unbuffered text #
note we are using the tokens imported instead of the constants

::

    from game.gamesrc.teltola.RTClient import HTML_TOKEN, JAVASCRIPT_TOKEN, UNENCODED_TOKEN
    hello_world_js = "alert('hello world');"
    welcome_html = "<h1>Hello World</h1>"
    session.msg("".join([JAVASCRIPT_TOKEN, hello_world_js, HTML_TOKEN, welcome_html, UNENCODED_TOKEN,"Hello there."]))

::

    session.msg(chr(243))
    session.msg(my_text_with_line_breaks)
    session.msg(chr(244))

Values of Tokens
================

+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| chr() value \| name \| function                                                                                                                                                                         |
+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| 240 \| HTML\_TOKEN \| lets client know it is about to receive HTML                                                                                                                                      |
+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| 241 \| JAVASCRIPT\_TOKEN \| lets client know it is about to receive javascript                                                                                                                          |
+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| 242 \| UNENCODED\_TOKEN \| lets client know it is about to receive plain telnet text                                                                                                                    |
+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| 243 \| NO\_AUTOCHUNK\_TOKEN \| applies to unencoded mode only, prevents the chunking of text at end-of-line characters so that only mode changes force the buffer to be sent to the client              |
+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| 244 \| AUTOCHUNK\_TOKEN \| applies to unencoded mode only, enables automatic chunking of text by end-of-line characters and by non-blank buffers not having been written to in the last 1/10th second   |
+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

identifying as an rtclient
--------------------------

rtclients send the text rtclient\\n immediately after connection so that
the server may enable rtclient extensions

Buffering Control
-----------------

Unbuffered output is not supported. There are two different buffering
methods supported. The default method is called AUTOCHUNK and applies
only to unencoded data (see data encoding section below). JAVASCRIPT and
HTML data is always treated as NO\_AUTOCHUNK.

NO\_AUTOCHUNK
~~~~~~~~~~~~~

Contents are never sent to the client until the encoding mode changes
(for example, switching from HTML to UNENCODED will send the HTML
buffer) or the buffering mode changes (for example, one could set
NO\_AUTOCHUNK, send some text, and set NO\_AUTOCHUNK again to force a
flush.

AUTOCHUNK
~~~~~~~~~

    It sends the buffer to the client as unencoded text whenever one of
    two things happen:

**the buffer is non-blank but hasn't had anything added to it very
recently (about 1/10th of a second)** the buffer ends with an
end-of-line character (10, 13, 255)

Autochunking strips end-of-line characters and the client adds in its
own EOL! If you would like to preserve them, send them from within
NO\_AUTOCHUNK.
