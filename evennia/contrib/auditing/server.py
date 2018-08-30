"""
Auditable Server Sessions:
Extension of the stock ServerSession that yields objects representing 
all user input and all system output.

Evennia contribution - Johnny 2017
"""

import os
import re
import socket

from django.utils import timezone
from django.conf import settings as ev_settings
from evennia.utils import logger, mod_import, get_evennia_version
from evennia.server.serversession import ServerSession

# Attributes governing auditing of commands and where to send log objects
AUDIT_CALLBACK = getattr(ev_settings, 'AUDIT_CALLBACK', None)
AUDIT_IN = getattr(ev_settings, 'AUDIT_IN', False)
AUDIT_OUT = getattr(ev_settings, 'AUDIT_OUT', False)
AUDIT_MASK_IGNORE = set(['@ccreate', '@create'] + getattr(ev_settings, 'AUDIT_IGNORE', []))
AUDIT_MASK_KEEP_BIGRAM = set(['create', 'connect', '@userpassword'] + getattr(ev_settings, 'AUDIT_MASK_KEEP_BIGRAM', []))

if AUDIT_CALLBACK:
    try:
        AUDIT_CALLBACK = mod_import(AUDIT_CALLBACK).output
        logger.log_info("Auditing module online.")
        logger.log_info("Recording user input = %s." % AUDIT_IN)
        logger.log_info("Recording server output = %s." % AUDIT_OUT)
    except Exception as e:
        logger.log_err("Failed to activate Auditing module. %s" % e)

class AuditedServerSession(ServerSession):
    """
    This class represents a player's session and is a template for
    both portal- and server-side sessions.

    Each connection will see two session instances created:

     1. A Portal session. This is customized for the respective connection
        protocols that Evennia supports, like Telnet, SSH etc. The Portal
        session must call init_session() as part of its initialization. The
        respective hook methods should be connected to the methods unique
        for the respective protocol so that there is a unified interface
        to Evennia.
     2. A Server session. This is the same for all connected accounts,
        regardless of how they connect.

    The Portal and Server have their own respective sessionhandlers. These
    are synced whenever new connections happen or the Server restarts etc,
    which means much of the same information must be stored in both places
    e.g. the portal can re-sync with the server when the server reboots.

    This particular implementation parses all server inputs and/or outputs and 
    passes a dict containing the parsed metadata to a callback method of your 
    creation. This is useful for recording player activity where necessary for 
    security auditing, usage analysis or post-incident forensic discovery.
    
    *** WARNING ***
    All strings are recorded and stored in plaintext. This includes those strings
    which might contain sensitive data (create, connect, @password). These commands
    have their arguments masked by default, but you must mask or mask any
    custom commands of your own that handle sensitive information.
    
    Installation:

    Designate this class as the SERVER_SESSION_CLASS in `settings.py`, then set
    some additional options concerning what to log and where to send it.
    
    settings.py:
    SERVER_SESSION_CLASS = 'evennia.contrib.auditing.server.AuditedServerSession'
    
    # Where to send logs? Define the path to a module containing a function 
    # called 'output()' you've written that accepts a dict object as its sole 
    # argument. From that function you can store/forward the message received
    # as you please. An example file-logger is below:
    AUDIT_CALLBACK = 'evennia.contrib.auditing.examples'
    
    # Log all user input? Be ethical about this; it will log all private and 
    # public communications between players and/or admins.
    AUDIT_IN = True/False
    
    # Log all server output? This will result in logging of ALL system
    # messages and ALL broadcasts to connected players, so on a busy MUD this 
    # will be very voluminous!
    AUDIT_OUT = True/False
    
    # What commands do you NOT want masked for sensitivity?
    AUDIT_MASK_IGNORE = ['@ccreate', '@create']
    
    # What commands do you want to keep the first two terms of, masking the rest?
    # This only triggers if there are more than two terms in the message.
    AUDIT_MASK_KEEP_BIGRAM = ['create', 'connect', '@userpassword']
    """
    def audit(self, **kwargs):
        """
        Extracts messages and system data from a Session object upon message 
        send or receive.
    
        Kwargs:
            src (str): Source of data; 'client' or 'server'. Indicates direction.
            text (list): Message sent from client to server.
            text (str): Message from server back to client.
    
        Returns:
            log (dict): Dictionary object containing parsed system and user data
                related to this message.

        """
        # Get time at start of processing
        time_obj = timezone.now()
        time_str = str(time_obj)
        
        # Sanitize user input
        session = self
        src = kwargs.pop('src', '?')
        bytes = 0
        
        if src == 'client':
            try:
                data = str(kwargs['text'][0][0])
            except IndexError:
                logger.log_err('Failed to parse client-submitted string!')
                return False
                
        elif src == 'server':
            # Server outputs can be unpredictable-- sometimes tuples, sometimes
            # plain strings. Try to parse both.
            try: 
                if isinstance(kwargs.get('text', ''), (tuple,list)):
                    data = kwargs['text'][0]
                elif not 'text' in kwargs and len(kwargs.keys()) == 1:
                    data = kwargs.keys()[0]
                else:
                    data = str(kwargs['text'])
                    
            except: data = str(kwargs)
            
        bytes = len(data.encode('utf-8'))
                
        data = data.strip()
            
        # Do not log empty lines
        if not data: return {}
        
        # Get current session's IP address
        client_ip = session.address
        
        # Capture Account name and dbref together
        account = session.get_account()
        account_token = ''
        if account: 
            account_token = '%s%s' % (account.key, account.dbref)
            
        # Capture Character name and dbref together
        char = session.get_puppet()
        char_token = ''
        if char:
            char_token = '%s%s' % (char.key, char.dbref)
            
        # Capture Room name and dbref together
        room = None
        room_token = ''
        if char:
            room = char.location
            room_token = '%s%s' % (room.key, room.dbref)
            
        # Mask any PII in message, where possible
        data = self.mask(data, **kwargs)
            
        # Compile the IP, Account, Character, Room, and the message.
        log = {
            'time': time_str,
            'hostname': socket.getfqdn(),
            'application': '%s' % ev_settings.SERVERNAME,
            'version': get_evennia_version(),
            'pid': os.getpid(),
            'direction': 'SND' if src == 'server' else 'RCV',
            'protocol': self.protocol_key,
            'ip': client_ip,
            'session': 'session#%s' % self.sessid,
            'account': account_token,
            'character': char_token,
            'room': room_token,
            'msg': '%s' % data,
            'bytes': bytes,
            'objects': {
                'time': time_obj,
                'session': self,
                'account': account,
                'character': char,
                'room': room,
            }
        }

        return log
        
    def mask(self, msg, **kwargs):
        """
        Masks potentially sensitive user information within messages before
        writing to log. Recording cleartext password attempts is bad policy.
    
        Args:
            msg (str): Raw text string sent from client <-> server
    
        Returns:
            msg (str): Text string with sensitive information masked out.

        """
        # Get command based on fuzzy match
        command = next((x for x in re.findall('^(?:Command\s\')*[\s]*([create]{5,6}|[connect]{6,7}|[@userpassword]{6,13}).*', msg, flags=re.IGNORECASE)), None)
        if not command or command in AUDIT_MASK_IGNORE:
            return msg
            
        # Break msg into terms
        terms = [x.strip() for x in re.split('[\s\=]+', msg) if x]
        num_terms = len(terms)
        
        # If the first term was typed correctly, grab the appropriate number
        # of subsequent terms and mask the remainder
        if command in AUDIT_MASK_KEEP_BIGRAM and num_terms >= 3:
            terms = terms[:2] + ['*' * sum([len(x.zfill(8)) for x in terms[2:]])]
        else:
            # If the first term was not typed correctly, doesn't have the right
            # number of terms or is clearly password-related,
            # only grab the first term (minimizes chances of capturing passwords
            # conjoined with username i.e. 'conect johnnypassword1234!').
            terms = [terms[0]] + ['*' * sum([len(x.zfill(8)) for x in terms[1:]])]
        
        msg = ' '.join(terms)
        return msg
    
    def data_out(self, **kwargs):
        """
        Generic hook for sending data out through the protocol.

        Kwargs:
            kwargs (any): Other data to the protocol.

        """
        if AUDIT_CALLBACK and AUDIT_OUT:
            try:
                log = self.audit(src='server', **kwargs)
                if log: AUDIT_CALLBACK(log, **kwargs)
            except Exception as e:
                logger.log_err(e)
        
        super(AuditedServerSession, self).data_out(**kwargs)
        
    def data_in(self, **kwargs):
        """
        Hook for protocols to send incoming data to the engine.

        Kwargs:
            kwargs (any): Other data from the protocol.

        """
        if AUDIT_CALLBACK and AUDIT_IN:
            try:
                log = self.audit(src='client', **kwargs)
                if log: AUDIT_CALLBACK(log, **kwargs)
            except Exception as e:
                logger.log_err(e)
            
        super(AuditedServerSession, self).data_in(**kwargs)
