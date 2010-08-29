"""
This module handles some of the -reply packets like whois-reply.
"""
#TODO: This is deprecated!
from src.objects.models import Object
from src.imc2 import imc_ansi

def handle_whois_reply(packet):
    try:
        pobject = Object.objects.get(id=packet.target)
        response_text = imc_ansi.parse_ansi(packet.optional_data.get('text', 
                                                                      'Unknown'))
        pobject.emit_to('Whois reply from %s: %s' % (packet.origin,
                                                     response_text))
    except Object.DoesNotExist:
        # No match found for whois sender. Ignore it.
        pass
