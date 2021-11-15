[![](https://1.bp.blogspot.com/-kMcLTjgmpa0/UQfBh7FsD7I/AAAAAAAABys/uGhAhtwG22s/s200/red_curtain_hand3crop_category.jpg)](https://1.bp.blogspot.com/-kMcLTjgmpa0/UQfBh7FsD7I/AAAAAAAABys/uGhAhtwG22s/s1600/red_curtain_hand3crop_category.jpg)

At the moment there are several Evennia projects churning along behind the scenes, none of which I've yet gotten to the point of pushing into a finished state.  Apart from bug fixes and other minor things happening, these are the main updates in the pipeline at the moment.  

### Multiple Characters per Player/Session

Evennia has for a long time enforced a clean separation between the _Player_ and the _Character._ It's a much appreciated feature among our users. The _Player_ is "you", the human playing the game. It knows your password, eventual user profile etc. The _Character_ is your avatar in-game. This setup makes it easy for a Player to have many characters, and to "puppet" characters - all you need to do is "disconnect" the Player object from the Character object, then connect to another Character object (assuming you are allowed to puppet that object, obviously). So far so good. 

  

What Evennia currently _doesn't_ support is being logged in with _different_ client sessions to the _same_ Player/account while puppeting _multiple_ characters _at the same time._ Currently multiple client sessions may log into the same Player account, but they will then all just act as separate views of the same action (all will see the same output, you can send commands from each but they will end up with the same Character). 

  

Allowing each session to control a separate Character suggests changing the way the session is tracked by the player and Character. This turns out to be more work than I originally envisioned when seeing the feature request in the issue tracker. But if my plan works out it will indeed become quite easy to use Evennia to both allow multi-play or not as you please, without having to remember separate passwords for each Character/account.

  

### Webserver change to Server level

Evennia consists of two main processes, the _Portal_ and the _Server._ The details of those were covered in an earlier blog post [here](http://evennia.blogspot.se/2012/08/combining-twisted-and-django.html). Evennia comes with a Twisted-based webserver which is currently operating on the _Portal_ level. This has the advantage of not being affected by Server-reboots. The drawback is however that being in a different process from the main Server, accessing the database and notably its server-side caches becomes a problem - changing the database from the Portal side does not automatically update the caches on the Server side, telling them that the database has changed. Also writing to the database from two processes may introduce race conditions. 

  

For our simple default setup (like a website just listing some database statistics) this is not a terrible problem, but as more users start to use Evennia, there is a growing interest in more advanced uses of the webserver. Several developers want to use the webserver to build game-related rich website experiences for their games - online character generation, tie-in forums and things like that. Out-of-sync caches then becomes a real concern. 

  

One way around this could be to implement a framework (such as memcached) for homogenizing caches across all Evennia processes. After lots of IRC discussions I'm going with what seems to be the more elegant and clean solution though - moving the webserver into the _Server_ process altogether. The _Portal_ side will thus only hold a web proxy and the webclient protocol. This way all database access will happen from the same process simplifying things a lot. It will make it much easier for users to use django to create rich web experiences without having to worry about pesky behind the scenes things like caches and the like. 

  

### Out-of-band communication 

This has been "brewing" for quite some time, I've been strangely unmotivated to finalize it. Out of band communication means the MUD client can send and receive data to/from the server directly, without the player having to necessesarily enter an active command or see any immediate effect. This could be things like updating a health bar in a client-side GUI, redirect text to a specific client window but also potentially more advanced stuff. I created the Evennia-side oob-handler over Christmas; it allows for client sessions to "sign up" for "listening" to attribute updates, do scheduled checks and so on. It's already in the codebase but is not activated nor tested yet.  
  
On the protocol side (for serializing data to the client) I have a MSDP implementation ready for telnet subnegotiation, it should be simple to add also GMCP once everything is tested. A JSON-based side channel for the webclient is already in place since a long time if I remember correctly, it just need to be connected to the server-side oob-handler once that's finished.