"""
Websocket-webclient

This implements a webclient with WebSockets (http://en.wikipedia.org/wiki/WebSocket)
by use of the txws implementation (https://github.com/MostAwesomeDude/txWS). It is
used together with src/web/media/javascript/evennia_websocket_webclient.js.

Thanks to Ricard Pillosu whose Evennia plugin inspired this module.

Communication over the websocket interface is done with normal text
communication. A special case is OOB-style communication; to do this
the client must send data on the following form:

    OOB{"func1":[args], "func2":[args], ...}

where the dict is JSON encoded. The initial OOB-prefix
is used to identify this type of communication, all other data
is considered plain text (command input).

Example of call from a javascript client:

    websocket = new WeSocket("ws://localhost:8021")
    var msg1 = "WebSocket Test"
    websocket.send(msg1)
    var msg2 = JSON.stringify({"testfunc":[[1,2,3], {"kwarg":"val"}]})
    websocket.send("OOB" + msg2)
    websocket.close()

"""
import json
from twisted.internet.protocol import Protocol
from src.server.session import Session
from src.utils.logger import log_trace
from src.utils.utils import to_str, make_iter
from src.utils.text2html import parse_html


class WebSocketClient(Protocol, Session):
    """
    Implements the server-side of the Websocket connection.
    """

    def connectionMade(self):
        """
        This is called when the connection is first established.
        """
        client_address = self.transport.client
        self.init_session("websocket", client_address, self.factory.sessionhandler)
        self.sessionhandler.connect(self)

    def disconnect(self, reason=None):
        """
        generic hook for the engine to call in order to
        disconnect this protocol.
        """
        if reason:
            self.data_out(text=reason)
        self.connectionLost(reason)

    def connectionLost(self, reason):
        """
        this is executed when the connection is lost for
        whatever reason. it can also be called directly, from
        the disconnect method
        """
        self.sessionhandler.disconnect(self)
        self.transport.close()

    def dataReceived(self, string):
        """
        Method called when data is coming in over
        the websocket connection.

        Type of data is identified by a 3-character
        prefix.
            OOB - This is an Out-of-band instruction. If so,
                  the remaining string should be a json-packed
                  string on the form {oobfuncname: [args, ], ...}
            any other prefix (or lack of prefix) is considered
                  plain text data, to be treated like a game
                  input command.
        """
        if string[:3] == "OOB":
            string = string[3:]
            try:
                oobdata = json.loads(string)
                for (key, args) in oobdata.items():
                    #print "oob data in:", (key, args)
                    self.data_in(text=None, oob=(key, make_iter(args)))
            except Exception:
                log_trace("Websocket malformed OOB request: %s" % string)
        else:
            # plain text input
            self.data_in(text=string)

    def sendLine(self, line):
        "send data to client"
        return self.transport.write(line)

    def data_in(self, text=None, **kwargs):
        """
        Data Websocket -> Server
        """
        self.sessionhandler.data_in(self, text=text, **kwargs)

    def data_out(self, text=None, **kwargs):
        """
        Data Evennia -> Player.
        generic hook method for engine to call in order to send data
        through the websocket connection.

        valid webclient kwargs:
            oob=<string> - supply an Out-of-Band instruction.
            raw=True - no parsing at all (leave ansi-to-html markers unparsed)
            nomarkup=True - clean out all ansi/html markers and tokens
        """
        try:
            text = to_str(text if text else "", encoding=self.encoding)
        except Exception, e:
            self.sendLine(str(e))
        if "oob" in kwargs:
            oobstruct = self.sessionhandler.oobstruct_parser(kwargs.pop("oob"))
            #print "oob data_out:", "OOB" + json.dumps(oobstruct)
            self.sendLine("OOB" + json.dumps(oobstruct))
        if "prompt" in kwargs:
            self.sendLine("PROMPT" + kwargs["prompt"])
        raw = kwargs.get("raw", False)
        nomarkup = kwargs.get("nomarkup", False)
        if raw:
            self.sendLine(text)
        else:
            self.sendLine(parse_html(text, strip_ansi=nomarkup))

