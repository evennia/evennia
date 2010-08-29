"""
This module contains all IMC2 events that are triggered periodically.
Most of these are used to maintain the existing connection and keep various
lists/caches up to date.
"""
# TODO: This is deprecated!

from time import time
#from src import events
#from src import scheduler
from src.imc2 import connection as imc2_conn
from src.imc2.packets import *
from src.imc2.trackers import IMC2_MUDLIST

class IEvt_IMC2_Send_IsAlive(events.IntervalEvent):
    """
    Event: Send periodic keepalives to network neighbors. This lets the other
    games know that our game is still up and connected to the network. Also
    provides some useful information about the client game.
    """
    def __init__(self):
        super(IEvt_IMC2_Send_IsAlive, self).__init__()
        self.name = 'IEvt_IMC2_Send_IsAlive'
        # Send keep-alive packets every 15 minutes.
        self.interval = 900
        self.description = "Send an IMC2 is-alive packet."
    
    def event_function(self):
        """
        This is the function that is fired every self.interval seconds.
        """
        try:
            imc2_conn.IMC2_PROTOCOL_INSTANCE.send_packet(IMC2PacketIsAlive())
        except AttributeError:
            #this will happen if we are not online in the first place
            #(like during development) /Griatch
            pass
        
class IEvt_IMC2_Send_Keepalive_Request(events.IntervalEvent):
    """
    Event: Sends a keepalive-request to connected games in order to see who
    is connected.
    """
    def __init__(self):
        super(IEvt_IMC2_Send_Keepalive_Request, self).__init__()
        self.name = 'IEvt_IMC2_Send_Keepalive_Request'
        self.interval = 3500
        self.description = "Send an IMC2 keepalive-request packet."
    
    def event_function(self):
        """
        This is the function that is fired every self.interval seconds.
        """
        imc2_conn.IMC2_PROTOCOL_INSTANCE.send_packet(IMC2PacketKeepAliveRequest())
        
class IEvt_IMC2_Prune_Inactive_Muds(events.IntervalEvent):
    """
    Event: Prunes games that have not sent is-alive packets for a while. If
    we haven't heard from them, they're probably not connected or don't
    implement the protocol correctly. In either case, good riddance to them.
    """
    def __init__(self):
        super(IEvt_IMC2_Prune_Inactive_Muds, self).__init__()
        self.name = 'IEvt_IMC2_Prune_Inactive_Muds'
        # Check every 30 minutes.
        self.interval = 1800
        self.description = "Check IMC2 list for inactive games."
        # Threshold for game inactivity (in seconds).
        self.inactive_thresh = 3599
    
    def event_function(self):
        """
        This is the function that is fired every self.interval seconds.
        """
        for name, mudinfo in IMC2_MUDLIST.mud_list.items():
            # If we haven't heard from the game within our threshold time,
            # we assume that they're dead.
            if time() - mudinfo.last_updated > self.inactive_thresh:
                del IMC2_MUDLIST.mud_list[name]

def add_events():
    """
    Adds the IMC2 events to the scheduler.
    """
    scheduler.add_event(IEvt_IMC2_Send_IsAlive())
    scheduler.add_event(IEvt_IMC2_Prune_Inactive_Muds())
    scheduler.add_event(IEvt_IMC2_Send_Keepalive_Request())
