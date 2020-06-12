# Python 3

> *Note: Evennia only supports Python 2.7+ at this time. This page gathers various development information relevant to server developers.*

Django can work with Python 2 and 3 already, though changes may be required to how the Evennia code
uses it. Twisted has much Python 3 compatibility, but not all modules within it have been ported
yet. The
[twisted.python.dist3](https://twistedmatrix.com/documents/current/api/twisted.python.dist3.html)
module gives some information about what's ported, and I'm compiling a list of missing modules with
related bug reports which can be found below. The list is based on a search for import statements in
the Evennia source code, please add anything that's missing.

Part of this process is expected to be writing more tests for Evennia. One encouraging recent port
to Python 3 in Twisted is its Trial test framework, which may need to be used by Evennia to ensure
it still works correctly with Twisted on Python 3.

# "Strings"
Broadly (and perhaps over-simplified):

* Twisted [expects bytes](http://twistedmatrix.com/trac/wiki/FrequentlyAskedQuestions#WhydontTwistedsnetworkmethodssupportUnicodeobjectsaswellasstrings)
* Django [expects "" to be unicode](https://docs.djangoproject.com/en/1.8/topics/python3/#unicode-literals)

I think we should use (roughly speaking) "" for unicode and b"" for bytes everywhere, but I need to look at the impacts of this more closely.

# Links

* http://twistedmatrix.com/documents/current/core/howto/python3.html
* https://twistedmatrix.com/trac/wiki/Plan/Python3
* [Twisted Python3 bugs](https://twistedmatrix.com/trac/query?status=assigned&status=new&status=reopened&group=status&milestone=Python-3.x)

# Twisted module status

x = not ported to Python 3
/ = ported to Python 3

* twisted.application.internet /
* twisted.application.service /
* twisted.conch x (not used directly)
 * ~https://twistedmatrix.com/trac/ticket/5102~ /
 * ~https://twistedmatrix.com/trac/ticket/4993~ /
* twisted.conch.insults.insults x
* twisted.conch.interfaces x
* twisted.conch.manhole x
* twisted.conch.manhole_ssh x
* twisted.conch.ssh.common x
* twisted.conch.ssh.keys x
   * ~https://twistedmatrix.com/trac/ticket/7998~ /
   * "twisted.conch.ssh.keys should be ported to Python 3"
* twisted.conch.ssh.userauth x
* twisted.conch.telnet x
* twisted.cred.checkers /
* twisted.cred.portal /
* twisted.internet.defer /
* twisted.internet.interfaces /
* twisted.internet.protocol /
* twisted.internet.reactor /
* twisted.internet.ssl /
* twisted.internet.task /
* twisted.internet.threads /
* twisted.protocols.amp x
 * ~https://twistedmatrix.com/trac/ticket/6833~ /
  * "Port twisted.protocols.amp to Python 3"
* twisted.protocols.policies /
* twisted.python.components /
* twisted.python.log /
* twisted.python.threadpool /
* twisted.web.http (x)
 * Partial support. Sufficient?
* twisted.web.resource /
* twisted.web.server (x)
 * Partial support. Sufficient?
* twisted.web.static /
* twisted.web.proxy /
* twisted.web.wsgi x
 * ~https://twistedmatrix.com/trac/ticket/7993~ /
   * "'twisted.web.wsgi' should be ported to Python 3"
   * Seems to be making good progress
* twisted.words.protocols.irc x
 * https://twistedmatrix.com/trac/ticket/6320
  * "Python 3 support for twisted.words.protocols.irc"
 * ~https://twistedmatrix.com/trac/ticket/6564~
  * "Replace usage of builtin reduce in twisted.words"
