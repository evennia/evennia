from traceback import format_exc
from asyncore import dispatcher
from asynchat import async_chat
import socket, asyncore, time
from django.db import models
from django.db import connection

from apps.config.models import CommandAlias
import sys
import scheduler
import functions_general
import session_mgr
import gameconf
import settings
import cmdtable
import initial_setup

class Server(dispatcher):
   """
   The main server class from which everything branches.
   """
   def __init__(self):
      self.cmd_alias_list = {}
      self.game_running = True
      
      # Database-specific startup optimizations.
      if settings.DATABASE_ENGINE == "sqlite3":
         self.sqlite3_prep()
         
      # Wipe our temporary flags on all of the objects.
      cursor = connection.cursor()
      cursor.execute("UPDATE objects_object SET nosave_flags=''")
      
      print '-'*50
      # Load command aliases into memory for easy/quick access.
      self.load_cmd_aliases()
      self.port = gameconf.get_configvalue('site_port')

      if gameconf.get_configvalue('game_firstrun') == '1':
         print ' Game started for the first time, setting defaults.'
         initial_setup.handle_setup()

      # Start accepting connections.
      dispatcher.__init__(self)
      self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
      self.set_reuse_addr()
      self.bind(('', int(self.port)))
      self.listen(100)
      self.start_time = time.time()

      print ' %s started on port %s.' % (gameconf.get_configvalue('site_name'), self.port,)
      print '-'*50
      
   """
   BEGIN SERVER STARTUP METHODS
   """
      
   def load_cmd_aliases(self):
      """
      Load up our command aliases.
      """
      alias_list = CommandAlias.objects.all()
      for alias in alias_list:
         self.cmd_alias_list[alias.user_input] = alias.equiv_command
      print ' Command Aliases Loaded: %i' % (len(self.cmd_alias_list),)
      
   def handle_accept(self):
      """
      What to do when we get a connection.
      """
      conn, addr = self.accept()
      session = session_mgr.new_session(self, conn, addr)
      session.game_connect_screen(session)
      print 'Connection:', str(session)
      print 'Sessions active:', len(session_mgr.get_session_list())
      
   def sqlite3_prep(self):
      """
      Optimize some SQLite stuff at startup since we can't save it to the
      database.
      """
      cursor = connection.cursor()
      cursor.execute("PRAGMA cache_size=10000")
      cursor.execute("PRAGMA synchronous=OFF")
      cursor.execute("PRAGMA count_changes=OFF")
      cursor.execute("PRAGMA temp_store=2")
      
   """
   BEGIN GENERAL METHODS
   """      
   def shutdown(self, message='The server has been shutdown. Please check back soon.'):
      functions_general.announce_all(message)
      self.game_running = False


   def command_list(self):
      """
      Return a string representing the server's command list.
      """
      clist = cmdtable.ctable.keys()
      clist.sort()
      return clist

   def reload(self, session):
      """
      Reload modules that don't have any variables that can be reset.
      For changes to the scheduler, server, or session_mgr modules, a cold
      restart is needed.
      """
      reload_list = ['ansi', 'cmdhandler', 'commands_comsys', 'commands_general',
         'commands_privileged', 'commands_unloggedin', 'defines_global',
         'events', 'functions_db', 'functions_general', 'functions_comsys',
         'functions_help', 'gameconf', 'session', 'apps.objects.models',
         'apps.helpsys.models', 'apps.config.models']
         
      for mod in reload_list:
         reload(sys.modules[mod])

      session.msg("Modules reloaded.")
      functions_general.log_infomsg("Modules reloaded by %s." % (session,))
   """
   END Server CLASS
   """   

"""
BEGIN MAIN APPLICATION LOGIC
"""
if __name__ == '__main__':
   server = Server()
   
   try:
      while server.game_running:
         asyncore.loop(timeout=5, count=1)
         scheduler.heartbeat()
                  
   except KeyboardInterrupt:
      server.shutdown()
      print '--> Server killed by keystroke.'

   except:
      server.shutdown(message="The server has encountered a fatal error and has been shut down. Please check back soon.")
      functions_general.log_errmsg("Untrapped error: %s" %
         (format_exc()))
