"""
This module contains all IMC2 events that are triggered periodically.
Most of these are used to maintain the existing connection and keep various
lists/caches up to date.
"""
from src import events
from src import scheduler
from src.imc2 import connection as imc2_conn
from src.imc2.packets import *

class IEvt_IMC2_KeepAlive(events.IntervalEvent):
    """
    Event: Send periodic keepalives to network neighbors. This lets the other
    games know that our game is still up and connected to the network. Also
    provides some useful information about the client game.
    """
    name = 'IEvt_IMC2_KeepAlive'
    # Send keep-alive packets every 15 minutes.
    interval = 900
    description = "Send an IMC2 keepalive packet."
    
    def event_function(self):
        """
        This is the function that is fired every self.interval seconds.
        """
        packet = IMC2PacketIsAlive()
        imc2_conn.IMC2_PROTOCOL_INSTANCE.send_packet(packet)

def add_events():
    """
    Adds the IMC2 events to the scheduler.
    """
    scheduler.add_event(IEvt_IMC2_KeepAlive())