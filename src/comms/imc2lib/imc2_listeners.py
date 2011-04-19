"""
This module handles some of the -reply packets like whois-reply.

"""
from src.objects.models import ObjectDB
from src.comms.imc2lib import imc2_ansi

def handle_whois_reply(packet):
    try:
        pobject = ObjectDB.objects.get(id=packet.target)
        response_text = imc2_ansi.parse_ansi(packet.optional_data.get('text', 'Unknown'))
        string = 'Whois reply from %s: %s' % (packet.origin, response_text)
        pobject.msg(string.strip())
    except ObjectDB.DoesNotExist:
        # No match found for whois sender. Ignore it.
        pass
