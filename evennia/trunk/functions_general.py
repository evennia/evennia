import session_mgr
"""
General commonly used functions.
"""

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
      
   days = seconds / 86400
   seconds -= days * 86400
   hours = seconds / 3600
   seconds -= hours * 3600
   minutes = seconds / 60
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
