"""
Auditable Server Sessions:
Extension of the stock ServerSession that yields objects representing 
user inputs and system outputs.

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
AUDIT_MASKS = [
    {'connect': r"^[@\s]*[connect]{5,8}\s+(\".+?\"|[^\s]+)\s+(?P<secret>.+)"},
    {'connect': r"^[@\s]*[connect]{5,8}\s+(?P<secret>[\w\\]+)"},
    {'create': r"^[^@]?[create]{5,7}\s+(\w+|\".+?\")\s+(?P<secret>[\w\\]+)"},
    {'create': r"^[^@]?[create]{5,7}\s+(?P<secret>[\w\\]+)"},
    {'userpassword': r"^[@\s]*[userpassword]{11,14}\s+(\w+|\".+?\")\s+=*\s*(?P<secret>[\w\\]+)"},
    {'password': r"^[@\s]*[password]{6,9}\s+(?P<secret>.*)"},
] + getattr(ev_settings, 'AUDIT_MASKS', [])

if AUDIT_CALLBACK:
    try:
        AUDIT_CALLBACK = getattr(mod_import('.'.join(AUDIT_CALLBACK.split('.')[:-1])), AUDIT_CALLBACK.split('.')[-1])
        logger.log_info("Auditing module online.")
        logger.log_info("Recording user input: %s" % AUDIT_IN)
        logger.log_info("Recording server output: %s" % AUDIT_OUT)
        logger.log_info("Log destination: %s" % AUDIT_CALLBACK)
    except Exception as e:
        logger.log_err("Failed to activate Auditing module. %s" % e)

class AuditedServerSession(ServerSession):
    """
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
    AUDIT_CALLBACK = 'evennia.contrib.auditing.outputs.to_file'
    
    # Log all user input? Be ethical about this; it will log all private and 
    # public communications between players and/or admins.
    AUDIT_IN = True/False
    
    # Log all server output? This will result in logging of ALL system
    # messages and ALL broadcasts to connected players, so on a busy MUD this 
    # will be very voluminous!
    AUDIT_OUT = True/False
    
    # Any custom regexes to detect and mask sensitive information, to be used
    # to detect and mask any sensitive custom commands you may develop.
    # Takes the form of a list of dictionaries, one k:v pair per dictionary
    # where the key name is the canonical name of a command and gets displayed
    # at the tail end of the message so you can tell which regex masked it.
    # The sensitive data itself must be captured in a named group with a
    # label of 'secret'.
    AUDIT_MASKS = [
        {'authentication': r"^@auth\s+(?P<secret>[\w]+)"},
    ]
    
    """
    def audit(self, **kwargs):
        """
        Extracts messages and system data from a Session object upon message 
        send or receive.
    
        Kwargs:
            src (str): Source of data; 'client' or 'server'. Indicates direction.
            text (str or list): Client sends messages to server in the form of
                lists. Server sends messages to client as string.
    
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
        bytecount = 0
        
        if src == 'client':
            try:
                data = str(kwargs['text'][0][0])
            except IndexError:
                logger.log_err('Failed to parse client-submitted string!')
                return False
                
        elif src == 'server':
            data = str(kwargs)
            
        bytecount = len(data.encode('utf-8'))
                
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
        data = self.mask(data)
            
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
            'bytes': bytecount,
            'objects': {
                'time': time_obj,
                'session': self,
                'account': account,
                'character': char,
                'room': room,
            }
        }

        return log
        
    def mask(self, msg):
        """
        Masks potentially sensitive user information within messages before
        writing to log. Recording cleartext password attempts is bad policy.
    
        Args:
            msg (str): Raw text string sent from client <-> server
    
        Returns:
            msg (str): Text string with sensitive information masked out.

        """
        # Check to see if the command is embedded within server output
        _msg = msg
        is_embedded = False
        match = re.match(".*Command.*'(.+)'.*is not available.*", msg, flags=re.IGNORECASE)
        if match:
            msg = match.group(1).replace('\\', '')
            submsg = msg
            is_embedded = True
        
        for mask in AUDIT_MASKS:
            for command, regex in mask.iteritems():
                try:
                    match = re.match(regex, msg, flags=re.IGNORECASE)
                except Exception as e:
                    logger.log_err(modified_regex)
                    logger.log_err(e)
                    continue
                    
                if match:
                    term = match.group('secret')
                    try:
                        masked = re.sub(term, '*' * len(term.zfill(8)), msg)
                    except Exception as e:
                        print(msg, regex, term)
                        quit()
                    
                    if is_embedded:
                        msg = re.sub(submsg, masked, _msg, flags=re.IGNORECASE)
                    else: msg = masked
                    
                    return '%s <Masked: %s>' % (msg, command)
                    
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
                if log: AUDIT_CALLBACK(log)
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
                if log: AUDIT_CALLBACK(log)
            except Exception as e:
                logger.log_err(e)
            
        super(AuditedServerSession, self).data_in(**kwargs)
