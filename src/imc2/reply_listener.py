"""
This module handles some of the -reply packets like whois-reply.
"""
from src.objects.models import Object

def handle_whois_reply(packet):
    try:
        pobject = Object.objects.get(id=packet.target)
        pobject.emit_to('Whois reply: %s' % packet.optional_data.get('text', 'Unknown'))
    except Object.DoesNotExist:
        # No match found for whois sender. Ignore it.
        pass