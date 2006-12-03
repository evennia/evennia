from asyncore import dispatcher
from asynchat import async_chat
import socket, asyncore, time, sys
from sessions import PlayerSession
from django.db import models
from apps.config.models import ConfigValue, CommandAlias
from apps.objects.models import Object, Attribute
from django.contrib.auth.models import User

#
## Begin: Time Functions
#

schedule = {'heal':100.0}
lastrun = {}

def heal():
        pass

# The timer loop
def Timer(timer):

   sched = schedule.iteritems()
   for i in sched:
      try: lastrun[i[0]]
      except: lastrun[i[0]] = time.time()

      diff = timer - lastrun[i[0]]

   # Every 100 seconds, run heal(), defined above.
   if diff >= schedule['heal']:
      heal()
      lastrun['heal'] = time.time()
                        
#
## End: Time Functions
#
  
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
         dbnum = object.id
         self.object_list[dbnum] = object
      print ' Objects Loaded: %d' % (len(self.object_list),)

   def load_objects_contents(self):
      """
      Populate the 'contents_list' list for each object.
      
      TODO: Make this a lot more efficient or merge into
      load_objects.
      """
      for key, object in self.object_list.iteritems():
         if object.location:
            object.location.contents_list.append(object)
      print '  * Object Inventories Populated'

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
   def create_user(self, session, uname, email, password):
      """
      Handles the creation of new users.
      """
      start_room = int(self.get_configvalue('player_dbnum_start'))
      start_room_obj = self.object_list[start_room]

      # The user's entry in the User table must match up to an object
      # on the object table. The id's are the same, we need to figure out
      # the next free unique ID to use and make sure the two entries are
      # the same number.
      uid = self.get_nextfree_dbnum()
      user = User.objects.create_user(uname, email, password)
      # It stinks to have to do this but it's the only trivial way now.
      user.id = uid
      user.save

      # Create a player object of the same ID in the Objects table.
      user_object = Object(id=uid, type=1, name=uname, location=start_room_obj)
      user_object.save()

      # Activate the player's session and set them loose.
      session.login(user)
      print 'Registration: %s' % (session,)
      session.push("Welcome to %s, %s.\n\r" % (self.get_configvalue('site_name'), session.name,))
         
   def announce_all(self, message, with_ann_prefix=True):
      """
      Announces something to all connected players.
      """
      if with_ann_prefix:
         prefix = 'Announcement:'
      else:
         prefix = ''
         
      for session in self.session_list:
         session.push('%s %s' % (prefix, message,))
      
   def get_configvalue(self, configname):
      """
      Retrieve a configuration value.
      """
      return self.configvalue[configname]
      
   def get_nextfree_dbnum(self):
      """
      Figure out what our next free database reference number is.
      """
      # First we'll see if there's an object of type 5 (GARBAGE) that we
      # can recycle.
      nextfree = Object.objects.filter(type__exact=5)
      if nextfree:
         # We've got at least one garbage object to recycle.
         #return nextfree.id
         return nextfree[0].id
      else:
         # No garbage to recycle, find the highest dbnum and increment it
         # for our next free.
         return Object.objects.order_by('-id')[0].id + 1
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
         asyncore.loop(timeout=5, count=1) # Timer() called every 5 seconds.
         Timer(time.time())
                  
   except KeyboardInterrupt:
      server.announce_all('The server has been shutdown. Please check back soon.\n\r')
      print '--> Server killed by keystroke.'
