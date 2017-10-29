"""
Trace a message through the messaging system
"""

import time


def timetrace(message, idstring, tracemessage="TEST_MESSAGE", final=False):
    """
    Trace a message with time stamps.

    Args:
        message (str): The actual message coming through
        idstring (str): An identifier string specifying where this trace is happening.
        tracemessage (str): The start of the message to tag.
            This message will get attached time stamp.
        final (bool): This is the final leg in the path - include total time in message

    """
    if message.startswith(tracemessage):
        # the message is on the form TEST_MESSAGE tlast t0
        # where t0 is the initial starting time and last is the time
        # saved at the last stop.
        try:
            prefix, tlast, t0 = message.split(None, 2)
            tlast, t0 = float(tlast), float(t0)
        except (IndexError, ValueError):
            t0 = time.time()
            tlast = t0
            t1 = t0
        else:
            t1 = time.time()
        # print to log (important!)
        print("** timetrace (%s): dT=%fs, total=%fs." % (idstring, t1 - tlast, t1 - t0))

        if final:
            message = " ****  %s (total %f) **** " % (tracemessage, t1 - t0)
        else:
            message = "%s %f %f" % (tracemessage, t1, t0)
    return message
