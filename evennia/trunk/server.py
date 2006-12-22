from asyncore import dispatcher
from asynchat import async_chat
import socket, asyncore, time, sys
from django.db import models
from django.db import connection

from apps.config.models import ConfigValue, CommandAlias
import scheduler
import functions_db
import functions_general
import global_defines
import session_mgr

class Server(dispatcher):
   """
   The main server class from which everything branches.
   """
   def __init__(self):
      self.cmd_alias_list = {}
      self.configvalue = {}
      self.game_running = True
      
      # Wipe our temporary flags on all of the objects.
      cursor = connection.cursor()
      cursor.execute("UPDATE objects_object SET nosave_flags=''")
      
      print '-'*50
      # Load stuff up into memory for easy/quick access.
      self.load_configvalues()
      self.load_cmd_aliases()
      
      # Start accepting connections.
      dispatcher.__init__(self)
      self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
      self.set_reuse_addr()
      self.bind(('', int(self.configvalue['site_port'])))
      self.listen(100)
      self.start_time = time.time()

      print ' %s started on port %s.' % (self.configvalue['site_name'], self.configvalue['site_port'],)
      print '-'*50
      
   """
   BEGIN SERVER STARTUP METHODS
   """
      
   def load_configvalues(self):
      """
      Loads our site's configuration up for easy access.
      """
      configs = ConfigValue.objects.all()
      
      for conf in configs:
         self.configvalue[conf.conf_key] = conf.conf_value
         
      print ' Configuration Loaded.'
      
   def load_cmd_aliases(self):
      """
      Load up our command aliases.
      """
      alias_list = CommandAlias.objects.all()
      for alias in alias_list:
         self.cmd_alias_list[alias.user_input] = alias.equiv_command
      print ' Aliases Loaded: %i' % (len(self.cmd_alias_list),)
      
   def handle_accept(self):
      """
      What to do when we get a connection.
      """
      conn, addr = self.accept()
      session = session_mgr.new_session(self, conn, addr)
      session.game_connect_screen(session)
      print 'Connection:', str(session)
      print 'Sessions active:', len(session_mgr.get_session_list())
      
   """
   BEGIN GENERAL METHODS
   """
   def add_object_to_cache(self, object):
      """
      Adds an object to the cached object list.
      """
      self.object_list[object.id] = object
      
   def remove_object_from_cache(self, object):
      """
      Removes an object from the cache.
      """
      if self.object_list.has_key(object.id):
         del self.object_list[object.id]
      else:
         print 'ERROR: Trying to remove non-cached object: %s' % (object,)
                  
   def get_configvalue(self, configname):
      """
      Retrieve a configuration value.
      """
      return self.configvalue[configname]
      
   def shutdown(self, message='The server has been shutdown. Please check back soon.'):
      functions_general.announce_all(message)
      self.game_running = False
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
