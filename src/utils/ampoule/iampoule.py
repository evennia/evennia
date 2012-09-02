from zope.interface import Interface

class IStarter(Interface):
    def startAMPProcess(ampChild, ampParent=None):
        """
        @param ampChild: The AMP protocol spoken by the created child.
        @type ampChild: L{twisted.protocols.amp.AMP}

        @param ampParent: The AMP protocol spoken by the parent.
        @type ampParent: L{twisted.protocols.amp.AMP}
        """

    def startPythonProcess(prot, *args):
        """
        @param prot: a L{protocol.ProcessProtocol} subclass
        @type prot: L{protocol.ProcessProtocol}

        @param args: a tuple of arguments that will be passed to the
                    child process.

        @return: a tuple of the child process and the deferred finished.
                 finished triggers when the subprocess dies for any reason.
        """

