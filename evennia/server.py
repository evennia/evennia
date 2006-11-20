from asyncore import dispatcher
from asynchat import async_chat
import socket, asyncore, time, sys
from sessions import PlayerSession
from django.db import models
from apps.config.models import Config
from apps.objects.models import Object

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
   def __init__(self, port):
      dispatcher.__init__(self)
      self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
      self.set_reuse_addr()
      self.bind(('', port))
      self.listen(100)
      self.session_list = []
      self.object_list = {}
      self.game_running = True
      print '-'*50
      self.load_config()
      self.load_objects()
      print ' Server started on port %i.' % (port,)
      print '-'*50
      
   def load_config(self):
      """
      Loads our site's configuration up for easy access.
      """
      self.config = Config.objects.all()[0]
      print ' Configuration Loaded.'
      
   def load_objects(self):
      """
      Load all of our objects into memory.
      """
      object_list = Object.objects.all()
      for object in object_list:
         dbnum = object.id
         self.object_list[dbnum] = object
      print ' Objects Loaded: %i' % (len(self.object_list),)
      
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

if __name__ == '__main__':
   server = Server(4000)

   try:
      while server.game_running:
         asyncore.loop(timeout=5, count=1) # Timer() called every 5 seconds.
         Timer(time.time())
                  
   except KeyboardInterrupt:
      print 'Interrupted'
