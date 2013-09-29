"""
Default Typeclass for Comms.

See objects.objects for more information on Typeclassing.
"""
from src.typeclasses.typeclass import TypeClass


class Comm(TypeClass):
    """
    This is the base class for all Comms. Inherit from this to create different
    types of communication channels.
    """
    def __init__(self, dbobj):
        super(Comm, self).__init__(dbobj)

    def format_message(self, msg):
        """
        Takes a Msg (see models.Msg), and derives the output display for it on
        the channel.
        """
