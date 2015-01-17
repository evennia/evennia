"""
This module implements a remote pool to use with AMP.
"""

from twisted.protocols import amp

class AMPProxy(amp.AMP):
    """
    A Proxy AMP protocol that forwards calls to a wrapped
    callRemote-like callable.
    """
    def __init__(self, wrapped, child):
        """
        @param wrapped: A callRemote-like callable that takes an
                        L{amp.Command} as first argument and other
                        optional keyword arguments afterwards.
        @type wrapped: L{callable}.

        @param child: The protocol class of the process pool children.
                      Used to forward only the methods that are actually
                      understood correctly by them.
        @type child: L{amp.AMP}
        """
        amp.AMP.__init__(self)
        self.wrapped = wrapped
        self.child = child

        localCd = set(self._commandDispatch.keys())
        childCd = set(self.child._commandDispatch.keys())
        assert localCd.intersection(childCd) == set(["StartTLS"]), \
                    "Illegal method overriding in Proxy"

    def locateResponder(self, name):
        """
        This is a custom locator to forward calls to the children
        processes while keeping the ProcessPool a transparent MITM.

        This way of working has a few limitations, the first of which
        is the fact that children won't be able to take advantage of
        any dynamic locator except for the default L{CommandLocator}
        that is based on the _commandDispatch attribute added by the
        metaclass. This limitation might be lifted in the future.
        """
        if name == "StartTLS":
            # This is a special case where the proxy takes precedence
            return amp.AMP.locateResponder(self, "StartTLS")

        # Get the dict of commands from the child AMP implementation.
        cd = self.child._commandDispatch
        if name in cd:
            # If the command is there, then we forward stuff to it.
            commandClass, _responderFunc = cd[name]
            # We need to wrap the doWork function because the wrapping
            # call doesn't pass the command as first argument since it
            # thinks that we are the actual receivers and callable is
            # already the responder while it isn't.
            doWork = lambda **kw: self.wrapped(commandClass, **kw)
            # Now let's call the right function and wrap the result
            # dictionary.
            return self._wrapWithSerialization(doWork, commandClass)
        # of course if the name of the command is not in the child it
        # means that it might be in this class, so fallback to the
        # default behavior of this module.
        return amp.AMP.locateResponder(self, name)

