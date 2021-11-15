[![](https://2.bp.blogspot.com/-2joU-U3OlH0/VvQ9hatC4MI/AAAAAAAAEic/PdL_kxHeXPE6O-HuM3Pk_6GQ5T19fc2zA/s320/supersonic-nozzle.png)](https://2.bp.blogspot.com/-2joU-U3OlH0/VvQ9hatC4MI/AAAAAAAAEic/PdL_kxHeXPE6O-HuM3Pk_6GQ5T19fc2zA/s1600/supersonic-nozzle.png)

Hi folks, a bit more technical entry this time. These usually go onto the Evennia mailing list but I thought it would be interesting to put it in the dev-blog for once.  
  
So, I'm now halfway through the [TODO list issue](https://github.com/evennia/evennia/issues/924) of the [wclient development branch](http://evennia.blogspot.se/2016/02/climbing-up-branches.html) as alluded to in the last post. The wclient branch aims to rework and beef up the web client infrastructure of Evennia.  
  
The first steps, which has been done a while was converting the SSH/SSL and IRC input/output protocols to use the new protocol infrastructure (telnet and websockets was done since before). That's just under-the-hood stuff though. Today I finished the changes to the Monitor/TickerHandlers, which may be of more general interest.  
  
With the changes to the the way OOB (Out-Of-Band) messages are passing through Evennia (see [this mailing list post](https://groups.google.com/forum/#!category-topic/evennia/evennia-news/xWQu_YVm14k) for more details), the **OOBHandler** is no more. As discussed there, the handling of incoming data is becoming a lot freer and will be easily expandable to everyone wanting to make for a custom client experience. The idea is thus for Evennia to offer _resources_ for various input commands to make use of, rather than prescribing such functionality in a monolothic way in the OOBHandler. There were three main functionalities the OOBHandler offered, and which will now be offered by separate components:  
  

1.  **Direct function callback.** The instruction from the client should be able to trigger a named server-side function. This is the core of the inputfunc system described previously.
2.  **Field/Attribute monitoring**. The client should be able to request _monitoring_ of an object's database fields or Attributes. For example, the client may request to be notified whenever the Character's "health" Attribute changes in some way. This is now handled by the new _monitorhandler_. See below.
3.  **Non-persistent function repeats.** One should be able to set up a repeating ticker that survives a server reload but does _not_ survive a cold shutdown - this mimics the life cycle of server Sessions. Scripts could do this already but I wanted to be able to use the TickerHandler for quick assignment. Problem was that the Tickerhandler in master branch is not only always-persistent, it also only calls _database_ _object methods_. So I have now expanded the tickerhandler to also accept arbitrary module functions, without any connection to a database object.

## The MonitorHandler   
  
**evennia.MONITOR_HANDLER** is the new singleton managing monitoring of on-object field/attribute changes. It is used like this:  
  

    MONITOR_HANDLER.add(obj, field_or_attrname, callback, **kwargs)

  
Here **obj** is a database entity, like a Character or another Object. The **field_or_attrname** is a string giving the name of a **db_*** database field (like **"db_key", "db_location"** etc). Any name not starting with **db_** is assumed to be the name of an on-object Attribute (like **"health"**). Henceforth, whenever this field or attribute changes in any way (that is, whenever it is re-saved to the database), the **callback** will be called with the optional **kwargs**, as well as a way to easily get to the changed value. As all handlers you can also list and remove monitors using the standard **MONITOR_HANDLER**.**remove()**, **.all()** etc.  
  
  
## The TickerHandler  
  
**evennia.TICKER_HANDLER** should be familiar to Evennia users from before - it's been around for a good while. It allows for creating arbitrary "tickers" that is being "subscribed" to - one ticker will call all subscribers rather than each object or function having its own timer.  
  
Before, the syntax for adding a new ticker required you specify a typeclassed entity and the name of the method on it to call every N seconds. This will now change. This is the new callsign for creating a new ticker:  
  

    TICKER_HANDLER.add(interval, callback, idstring="", persistent=True, *args, **kwargs)

  
Here**, interval,** like before, defines how often to call **callback(*args, **kwargs)**.  
  
The big change here is that **callback** should be given as a valid, already imported callable, which can be _either_ an on-entity method (like obj.func) or a global function in any module (like world.test.func) - the TickerHandler will analyze it and internally store it properly.  
  
**idstring** works as before, to separate tickers with the same intervals. Finally **persistent**=**False** means the ticker will behave the same way a Script with **persistent=False** does: it will survive a server reload but will _not_ survive a server shutdown. This latter functionality is particularly useful for client-side commands since the client Session will also not survive a shutdown.  
  
... So this is a rather big API change to the TickerHandler, which will mean some conflicts for those of you relying heavily on tickers. Easiest will definitely be to simply stop the old and start new ones. It's not clear yet if we'll offer some automated way to convert old tickers to new ones. Chime in if this is something important to you.  
  
## Happening Next  
  
The next steps involves making use of these new utilities to implement the basic OOB commands recommended by the MSDP and GMCP protocols along with some recommended functionality. We'll see how long that takes, but progress is being made. And if you are a web guy, do consider [helping out.](https://github.com/evennia/evennia/issues/924)  