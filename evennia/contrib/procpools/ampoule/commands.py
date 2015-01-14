from twisted.protocols import amp

class Shutdown(amp.Command):
    responseType = amp.QuitBox

class Ping(amp.Command):
    response = [('response', amp.String())]

class Echo(amp.Command):
    arguments = [('data', amp.String())]
    response = [('response', amp.String())]
