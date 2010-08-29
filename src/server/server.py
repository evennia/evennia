"""
This module implements the main Evennia
server process, the core of the game engine. 
"""
import time
import sys
import os
if os.name == 'nt':
    # For Windows batchfile we need an extra path insertion here.
    sys.path.insert(0, os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))))

from twisted.application import internet, service
from twisted.internet import protocol, reactor
from django.db import connection
from django.conf import settings

from src.config.models import ConfigValue
from src.server.session import SessionProtocol
from src.server import sessionhandler
from src.server import initial_setup
from src.utils import reloads
from src.utils.utils import get_evennia_version
from src.comms import channelhandler

class EvenniaService(service.Service):
    """
    The main server service task.
    """    
    def __init__(self):
        # Holds the TCP services.
        self.service_collection = None
        self.game_running = True
        sys.path.append('.')

        # Database-specific startup optimizations.
        if (settings.DATABASE_ENGINE == "sqlite3"
            or hasattr(settings, 'DATABASE')   
            and settings.DATABASE.get('ENGINE', None) == 'django.db.backends.sqlite3'):            
            # run sqlite3 preps
            self.sqlite3_prep()
            
        # Begin startup debug output.
        print '\n' + '-'*50
        
        last_initial_setup_step = \
                       ConfigValue.objects.conf('last_initial_setup_step')

        if not last_initial_setup_step:
            # None is only returned if the config does not exist,
            # i.e. this is an empty DB that needs populating.
            print ' Server started for the first time. Setting defaults.'
            initial_setup.handle_setup(0)
            print '-'*50

        elif int(last_initial_setup_step) >= 0: 
            # last_setup_step >= 0 means the setup crashed
            # on one of its modules and setup will resume, retrying
            # the last failed module. When all are finished, the step
            # is set to -1 to show it does not need to be run again. 
            print ' Resuming initial setup from step %s.' % \
                  last_initial_setup_step  
            initial_setup.handle_setup(int(last_initial_setup_step))
            print '-'*50

        # we have to null this here.
        sessionhandler.change_session_count(0)            

        self.start_time = time.time()

        # initialize channelhandler
        channelhandler.CHANNELHANDLER.update()
        # init all global scripts
        reloads.reload_scripts(init_mode=True)

        # Make output to the terminal. 
        print ' %s (%s) started on port(s):' % \
              (settings.SERVERNAME, get_evennia_version())
        for port in settings.GAMEPORTS:
            print '  * %s' % (port)              
        print '-'*50

        
                
    # Server startup methods

    def sqlite3_prep(self):
        """
        Optimize some SQLite stuff at startup since we
        can't save it to the database.
        """
        cursor = connection.cursor()
        cursor.execute("PRAGMA cache_size=10000")
        cursor.execute("PRAGMA synchronous=OFF")
        cursor.execute("PRAGMA count_changes=OFF")
        cursor.execute("PRAGMA temp_store=2")
        

    # General methods
    
    def shutdown(self, message=None):
        """
        Gracefully disconnect everyone and kill the reactor.
        """
        if not message:
            message = 'The server has been shutdown. Please check back soon.'
        sessionhandler.announce_all(message)
        sessionhandler.disconnect_all_sessions()
        reactor.callLater(0, reactor.stop)
        
    def getEvenniaServiceFactory(self):
        "Retrieve instances of the server"
        factory = protocol.ServerFactory()
        factory.protocol = SessionProtocol
        factory.server = self
        return factory

    def start_services(self, application):
        """
        Starts all of the TCP services.
        """
        self.service_collection = service.IServiceCollection(application)
        for port in settings.GAMEPORTS:
            evennia_server = \
                internet.TCPServer(port, self.getEvenniaServiceFactory())
            evennia_server.setName('Evennia%s' %port)
            evennia_server.setServiceParent(self.service_collection)
        
        if settings.IMC2_ENABLED:
            from src.imc2.connection import IMC2ClientFactory
            from src.imc2 import events as imc2_events
            imc2_factory = IMC2ClientFactory()
            svc = internet.TCPClient(settings.IMC2_SERVER_ADDRESS, 
                                     settings.IMC2_SERVER_PORT, 
                                     imc2_factory)
            svc.setName('IMC2')
            svc.setServiceParent(self.service_collection)
            imc2_events.add_events()

        if settings.IRC_ENABLED:
            from src.irc.connection import IRC_BotFactory
            irc = internet.TCPClient(settings.IRC_NETWORK, 
                                     settings.IRC_PORT, 
                                     IRC_BotFactory(settings.IRC_CHANNEL,
                                                    settings.IRC_NETWORK,
                                                    settings.IRC_NICKNAME))            
            irc.setName("%s:%s" % ("IRC", settings.IRC_CHANNEL))
            irc.setServiceParent(self.service_collection)


# Twisted requires us to define an 'application' attribute.
application = service.Application('Evennia') 
# The main mud service. Import this for access to the server methods.
mud_service = EvenniaService()
mud_service.start_services(application)
