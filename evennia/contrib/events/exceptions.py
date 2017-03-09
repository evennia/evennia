"""
Module containing the exceptions of the event system.
"""

class InterruptEvent(RuntimeError):

    """
    Interrupt the current event.

    You shouldn't have to use this exception directly, probably use the
    `deny()` function that handles it instead.

    """

    pass
