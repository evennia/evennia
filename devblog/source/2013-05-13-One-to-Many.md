[![](https://4.bp.blogspot.com/-M_YNUYvWuiw/UZCNa-U24lI/AAAAAAAAB2o/6wZzFjpCSvk/s320/one-in-many.jpg)](https://4.bp.blogspot.com/-M_YNUYvWuiw/UZCNa-U24lI/AAAAAAAAB2o/6wZzFjpCSvk/s1600/one-in-many.jpg)

As of yesterday, I completed and merged the first of the three upcoming Evennia features I mentioned in my [Churning Behind the Scenes](http://evennia.blogspot.se/2013/01/churning-behind-scenes.html) blog post: the "Multiple Characters per Player" feature.  
  
Evennia makes a strict division between _Player_ (this is an object storing login-info and represents the person connecting to the game) and their _Character_ (their representation in-game; Characters are just Objects with some nice defaults). When you log into the game with a client, a _Session_ tracks that particular connection.  
  
Previously the Player class would normally only handle one Session at a time. This made for an easy implementation and this behavior is quite familiar to users of many other mud code bases. There was an option to allow more than one Session, but each were then treated equally: all Sessions would see the same returns and the same in-game entities were controlled by all (and giving the quit command from one would kick all out).  
  
What changed now is that the Player class will manage each Session separately, without interfering with other Sessions connected to the same Player. Each Session can be connected, through the Player, to an individual Character. So multiple Characters could in principle be controlled simultaneously by the same real-world player using different open mud clients. This gives a lot of flexibility for games supporting multi-play but also as a nice way to transparently puppet temporary extras in heavy roleplaying games.  
  
It is still possible to force Evennia to accept only one Session per Player just like before, but this is now an option, not a limitation. And even in hardcore one-character-at-a-time roleplaying games it is nice for builders and admins to be able to have separate staff or npc characters without needing a separate account for each.  
  
This feature took a lot more work than I anticipated - it consitutes a lot of under-the-hood changes. But it also gave me ample opportunity to fix and clean up older systems and fix bugs. The outcome is more consistency and standardization in several places. There are plenty of other noteworthy changes that were made along the way in the dev branch along with some API changes users should be aware of.  
So if you are an Evennia game developer you should peek at the more detailed mailing list  [announcement](https://groups.google.com/forum/#!topic/evennia/EjAW8S2N86I) on what has changed. The wiki is not updated yet, that will come soon.  
  
Now onward to the next feature!