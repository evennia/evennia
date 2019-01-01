This directory contains Evennia's log files. The existence of this README.md file is also necessary
to correctly include the log directory in git (since log files are ignored by git and you can't
commit an empty directory). 

- `server.log` - log file from the game Server.
- `portal.log` - log file from Portal proxy (internet facing)

Usually these logs are viewed together with `evennia -l`. They are also rotated every week so as not
to be too big. Older log names will have a name appended by `_month_date`. 
 
- `lockwarnings.log` - warnings from the lock system.
- `http_requests.log` - this will generally be empty unless turning on debugging inside the server.

- `channel_<channelname>.log` - these are channel logs for the in-game channels They are also used
  by the `/history` flag in-game to get the latest message history. 
