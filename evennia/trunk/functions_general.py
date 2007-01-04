import session_mgr
import commands_privileged
import commands_general
import commands_unloggedin
"""
General commonly used functions.
"""
def print_errmsg(errormsg):
   """
   Prints/logs an error message. Pipe any errors to be logged through here.
   For now we're just printing to standard out.
   """
   print 'ERROR: %s' % (errormsg,)

def command_list():
   """
   Return a list of all commands.
   """
   commands = dir(commands_unloggedin) + dir(commands_general)
   stf_commands = dir(commands_privileged)
   filtered = [prospect for prospect in commands if "cmd_" in prospect]
   stf_filtered = [prospect for prospect in stf_commands if "cmd_" in prospect]
   processed = []
   for cmd in filtered:
      processed.append(cmd[4:])
   for cmd in stf_filtered:
      processed.append('@%s' %(cmd[4:],))
   return processed
   
def time_format(seconds, style=0):
   """
   Function to return a 'prettified' version of a value in seconds.
   
   Style 0: 1d 08:30
   Style 1: 1d
   Style 2: 1 day, 8 hours, 30 minutes, 10 seconds
   """
   if seconds < 0:
      seconds = 0
   else:
      # We'll just use integer math, no need for decimal precision.
      seconds = int(seconds) 
      
   days     = seconds / 86400
   seconds -= days * 86400
   hours    = seconds / 3600
   seconds -= hours * 3600
   minutes  = seconds / 60
   seconds -= minutes * 60
   
   if style is 0:
      """
      Standard colon-style output.
      """
      if days > 0:
         retval = '%id %02i:%02i' % (days, hours, minutes,)
      else:
         retval = '%02i:%02i' % (hours, minutes,)
      
      return retval
   elif style is 1:
      """
      Simple, abbreviated form that only shows the highest time amount.
      """
      if days > 0:
         return '%id' % (days,)
      elif hours > 0:
         return '%ih' % (hours,)
      elif minutes > 0:
         return '%im' % (minutes,)
      else:
         return '%is' % (seconds,)
         
   elif style is 2:
      """
      Full-detailed, long-winded format.
      """
      days_str = hours_str = minutes_str = ''
      if days > 0:
         days_str = '%i days, ' % (days,)
      if days or hours > 0:
         hours_str = '%i hours, ' % (hours,)
      if hours or minutes > 0:
         minutes_str = '%i minutes, ' % (minutes,)
      seconds_str = '%i seconds' % (seconds,)
      
      retval = '%s%s%s%s' % (days_str, hours_str, minutes_str, seconds_str,)
      return retval  

def announce_all(message, with_ann_prefix=True, with_nl=True):
   """
   Announces something to all connected players.
   """
   if with_ann_prefix:
      prefix = 'Announcement:'
   else:
      prefix = ''
      
   if with_nl:
      newline = '\r\n'
   else:
      newline = ''
      
   for session in session_mgr.get_session_list():
      session.msg_no_nl('%s %s%s' % (prefix, message,newline,))

def word_wrap(text, width=78):
   """
   A word-wrap function that preserves existing line breaks
   and most spaces in the text. Expects that existing line
   breaks are posix newlines (\n).
    
   Function originally by Mike Brown
   """
   return reduce(lambda line, word, width=width: '%s%s%s' %
                 (line,
                  ' \n'[(len(line)-line.rfind('\n')-1
                        + len(word.split('\n',1)[0]
                             ) >= width)],
                  word),
                 text.split(' ')
                )
