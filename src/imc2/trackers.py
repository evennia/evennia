"""
Certain periodic packets are sent by connected MUDs (is-alive, user-cache,
etc). The IMC2 protocol assumes that each connected MUD will capture these and
populate/maintain their own lists of other servers connected. This module
contains stuff like this. 
"""
from time import time

class IMC2Mud(object):
    """
    Stores information about other games connected to our current IMC2 network.
    """
    def __init__(self, packet):
        self.name = packet.origin
        self.versionid = packet.optional_data.get('versionid', None)
        self.networkname = packet.optional_data.get('networkname', None)
        self.url = packet.optional_data.get('url', None)
        self.host = packet.optional_data.get('host', None)
        self.port = packet.optional_data.get('port', None)
        self.sha256 = packet.optional_data.get('sha256', None)
        # This is used to determine when a Mud has fallen into inactive status.
        self.last_updated = time()
        
class IMC2MudList(object):
    """
    Keeps track of other MUDs connected to the IMC network.
    """
    def __init__(self):
        # Mud list is stored in a dict, key being the IMC Mud name.
        self.mud_list = {}
        
    def update_mud_from_packet(self, packet):
        # This grabs relevant info from the packet and stuffs it in the
        # Mud list for later retrieval.
        mud = IMC2Mud(packet)
        self.mud_list[mud.name] = mud
        
    def remove_mud_from_packet(self, packet):
        # Removes a mud from the Mud list when given a packet.
        mud = IMC2Mud(packet)
        try:
            del self.mud_list[mud.name]
        except KeyError:
            # No matching entry, no big deal.
            pass

# Use this instance to keep track of the other games on the network.
IMC2_MUDLIST = IMC2MudList()