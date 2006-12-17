from asyncore import dispatcher
from asynchat import async_chat
import socket, asyncore, time, sys
from sessions import PlayerSession
from django.db import models
from apps.config.models import ConfigValue, CommandAlias
from apps.objects.models import Object, Attribute
from django.contrib.auth.models import User
from scheduler import Scheduler
import functions_db
import functions_general

class Server(dispatcher):
   """
   The main server class from which everything branches.
   """
   def __init__(self):
      self.session_list = []
      self.object_list = {}
      self.cmd_alias_list = {}
      self.configvalue = {}
      self.game_running = True
      
      print '-'*50
      # Load stuff up into memory for easy/quick access.
      self.load_configvalues()
      self.load_objects()
      self.load_objects_contents()
      self.load_attributes()
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
      
   def load_objects(self):
      """
      Load all of our objects into memory.
      """
      object_list = Object.objects.all()
      for object in object_list:
         object.load_flags()
         dbnum = object.id
         self.object_list[dbnum] = object
      print ' Objects Loaded: %d' % (len(self.object_list),)

   def load_objects_contents(self):
      """
      Populate the 'contents_list' list for each object.
      
      TODO: This thing is just completely shot. No idea what's going on but
      it's bad mojo.
      """
      """
      object_list = Object.objects.all()
      for object in object_list:
         if object.location and not object.is_room():
            object.load_to_location()
            #print 'Adding %s to %s' % (object.id, object.location.id,)
      for object in object_list:
         print 'OBJ: %s CON: %s' % (object.id, object.location,)
      print '  * Object Inventories Populated'
      """

   def load_attributes(self):
      """
      Load all of our attributes into memory.
      """
      attribute_list = Attribute.objects.all()
      for attrib in attribute_list:
         attrib.object.attrib_list[attrib.name] = attrib.value
      print ' Attributes Loaded: %d' % (len(attribute_list),)
      
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
      session = PlayerSession(self, conn, addr)
      session.game_connect_screen(session)
      print 'Connection:', str(session)
      self.session_list.append(session)
      print 'Sessions active:', len(self.session_list)
      
   """
   BEGIN GENERAL METHODS
   """
   def add_object_to_cache(self, object):
      """
      Adds an object to the cached object list.
      """
      self.object_list[object.id] = object
                  
   def get_configvalue(self, configname):
      """
      Retrieve a configuration value.
      """
      return self.configvalue[configname]
      
   def get_session_list(self):
      """
      Lists the server's connected session objects.
      """
      return self.session_list
      
   def remove_session(self, session):
      """
      Removes a session from the server's session list.
      """
      self.session_list.remove(session)
      
   def shutdown(self, message='The server has been shutdown. Please check back soon.'):
      functions_general.announce_all(server, message)
      self.game_running = False
   """
   END Server CLASS
   """   

"""
BEGIN MAIN APPLICATION LOGIC
"""
if __name__ == '__main__':
   server = Server()
   scheduler = Scheduler(server)
   
   try:
      while server.game_running:
         asyncore.loop(timeout=5, count=1)
         scheduler.heartbeat()
                  
   except KeyboardInterrupt:
      server.shutdown()
      print '--> Server killed by keystroke.'
