[![](https://3.bp.blogspot.com/-82MT42ksmuU/U7FpMy-LgGI/AAAAAAAADqA/ok6MfvNNTvY/s1600/spiderweb.jpg)](https://3.bp.blogspot.com/-82MT42ksmuU/U7FpMy-LgGI/AAAAAAAADqA/ok6MfvNNTvY/s1600/spiderweb.jpg)

Latest Evennia come with a range of improvements, mainly related to its integration with the web.  
  

### New and improved ways to expand the website/webclient

  
Thanks to the work of contributor Kelketek, Evennia's Django-based web system (website and webclient) has been restructured to be much easier to expand. Previously you had to basically copy the entire web/ folder into your game and modify things in-place. This was not ideal since it made it inherently harder to update when things changed upstream. Now Evennia makes use of Django's _collectstatic_ functionality to allow people to plugin and overload only the media files and templates that they need. Kelketek wrote a new and shiny [web tutorial](https://github.com/evennia/evennia/wiki/Web%20Tutorial) explaining just how things work.   
  
  

### Websocket-based webclient with OOB

  
Evennia's webclient was an ajax-based one using a long polling ("comet") paradigm to work. These days all modern browsers support [websockets](http://en.wikipedia.org/wiki/WebSocket) though, a protocol that allows asynchronous server-client communication without the cludgery of long polling. So Evennia's new webclient will now use websockets if the browser supports it and fall back to the old comet client if it does not.  
  
The new client also has full support for OOB (Out-of-band) communication. The client uses JSON for straight forward OOB messaging with the server. As part of this, I had an excuse to go back to clean up and make the OOB backbone of Evennia more complete. The server-side oob commands are borrowed from [MSDP](http://tintin.sourceforge.net/msdp/) but the server side is of course independent of communication protocol (so webclient and telnet extensions can call the same server-side callbacks). I've not yet finalized the documentation for how to use the OOB yet, that will come soon-ish.