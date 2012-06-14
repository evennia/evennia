"""
This module handles some of the -reply packets like whois-reply.

"""
from src.objects.models import ObjectDB
from src.comms.imc2lib import imc2_ansi

from django.utils.translation import ugettext as _

def handle_whois_reply(packet):
    """
    When the player sends an imcwhois <playername> request, the outgoing
    packet contains the id of the one asking. This handler catches the
    (possible) reply from the server, parses the id back to the
    original asker and tells them the result.
    """
    try:
        pobject = ObjectDB.objects.get(id=packet.target)
        response_text = imc2_ansi.parse_ansi(packet.optional_data.get('text', 'Unknown'))
        string = _('Whois reply from %(origin)s: %(msg)s') % {"origin":packet.origin, "msg":response_text}
        pobject.msg(string.strip())
    except ObjectDB.DoesNotExist:
        # No match found for whois sender. Ignore it.
        pass
