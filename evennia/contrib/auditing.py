"""

Contribution - Johnny 2017

This is an extension of the base ServerSession class that parses
all server inputs and/or outputs and passes a dict containing the parsed
metadata to a method of your choosing.

This is useful for recording player activity where necessary for auditing,
usage data or post-incident forensic analysis.

Somewhere in your game (or even right there in settings.py) should be a 
method that receives dict objects and does something with them, whether 
writing to a database, a file, or some external queue. A simplistic example 
might be something as brief as:

from django.utils import timezone
from evennia.utils.logger import log_file
import json

def just_write_it(data, **kwargs):
    # Bucket logs by day
    bucket = timezone.now().strftime('%Y%m%d')
    # Remove the objects; keep the values
    data.pop('objects')
    # Write it
    log_file(json.dumps(data), filename="auditing_%s.log" % bucket)

The parsed metadata contains the account name and ID, the character name 
and ID, the room name and ID, and the IP address of the connected session
issuing the command. The respective objects are also passed in the event
you wish to store data back to them or manipulate them in some other way.

*** WARNING ***
All strings are recorded and stored in plaintext. This includes those strings
which might contain sensitive data (create, connect, password).

You are expected to implement proper masking/scrubbing of these and any
other commands upon receipt and storing the recorded data securely. Please do
not store user passwords in plaintext, and be ethical-- this records even
private communications.
***************

Installation:

Designate this class as the SERVER_SESSION_CLASS in `settings.py`.

i.e. SERVER_SESSION_CLASS = "evennia.contrib.auditing.AuditedServerSession"

There are three additional settings that govern operation-- whether you
want to record inbound strings and/or outbound strings, and what method
you want the data sent to.

AUDIT_METHOD = just_write_it
AUDIT_IN = True or False
AUDIT_OUT = True or False

Recording outbound strings can be noisy-- a single message broadcast to 12
occupants of a room will generate 12 of the same message, one to each.
"""

import os
import socket

from django.utils import timezone
from evennia import settings as ev_settings
from evennia.utils import logger
from evennia.server.serversession import ServerSession

class AuditedServerSession(ServerSession):
    def __init__(self, *args, **kwargs):
        super(AuditedServerSession, self).__init__(*args, **kwargs)
        
        # Attributes governing auditing of commands and where to send logs
        self.audit_method = getattr(ev_settings, 'AUDIT_METHOD', None)
        self.audit_in = getattr(ev_settings, 'AUDIT_IN', False)
        self.audit_out = getattr(ev_settings, 'AUDIT_OUT', False)
    
    def audit(self, **kwargs):
        """
        Creates a log entry from the given session.
        """
        # Sanitize user input
        session = self
        src = kwargs.get('src', '?')
        
        if src == 'client':
            try:
                data = kwargs['text'][0][0].strip()
            except IndexError:
                logger.log_err("Failed to log %s" % kwargs['text'])
                return False
                
        elif src == 'server':
            try:
                data = kwargs['text'].strip()
            except:
                data = str(kwargs)
            
        # Do not log empty lines
        if not data: return False
        
        # Get current session's IP address
        ip_token = session.address
        
        # Capture Account name and dbref together
        account = None
        account = session.get_account()
        account_token = 'null'
        if account: 
            account_token = '%s%s' % (account.key, account.dbref)
            
        # Capture Character name and dbref together
        char = None
        char = session.get_puppet()
        char_token = 'null'
        if char:
            char_token = '%s%s' % (char.key, char.dbref)
            
        # Capture Room name and dbref together
        room = None
        room_token = 'null'
        if char:
            room = char.location
            room_token = '%s%s' % (room.key, room.dbref)
            
        # Compile the IP, Account, Character, Room, and the message.
        parsed = {
            'time': str(timezone.now()),
            'hostname': socket.getfqdn(),
            'application': '%s_server' % ev_settings.SERVERNAME,
            'pid': os.getpid(),
            'values': {
                'src': src,
                'ip': ip_token,
                'account': account_token,
                'character': char_token,
                'room': room_token,
                'msg': '%s' % data,
            },
            'objects': {
                'session': self,
                'account': account,
                'character': char,
                'room': room,
            }
        }
        
        return parsed
    
    def data_out(self, **kwargs):
        """
        Sending data from Evennia->Client
        """
        if self.audit_method and self.audit_out:
            self.audit_method(self.audit(src='server', **kwargs))
        
        super(AuditedServerSession, self).data_out(**kwargs)
        
    def data_in(self, **kwargs):
        """
        Receiving data from the client
        """
        if self.audit_method and self.audit_in:
            self.audit_method(self.audit(src='client', **kwargs))
            
        super(AuditedServerSession, self).data_in(**kwargs)