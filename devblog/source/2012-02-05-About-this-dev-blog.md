This is to be my [Evennia](http://www.evennia.com/) dev blog, but it will also cover various other musings concerning programming in general and mud designing in particular. Whereas the Evennia [mailing list](https://groups.google.com/forum/#%21forum/evennia) remains the main venue for discussion, I will probably use this blog for announcing features too.  
  
Some background:  
Evennia is a Python MUD/MUX/MU* server. More correct is probably to call it a "MUD-building system". The developer codes their entire game using normal Python modules. All development is done with the full power of Python - gritty stuff like database operations and network communication are hidden away behind custom classes that you can treat and modify mostly like any Python primitives.  
  
Since the server is based on the [Twisted](http://twistedmatrix.com/trac/) and [Django](https://www.djangoproject.com/) technologies we can offer many modern features out of the box. Evennia is for example its own web server and comes with both its own website and an "comet"-style browser mud client. But before this turns into even more of a sales pitch, I'll just just direct you to the evennia website if you want to know more. :)  
  
I, Griatch, took over the development of Evennia from the original author, Greg Taylor, in 2010.