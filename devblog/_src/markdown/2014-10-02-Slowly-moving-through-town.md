[![](https://4.bp.blogspot.com/-LEAcNfC4EmQ/VC1ySqlz7cI/AAAAAAAAEO4/yVEgs7T6jlo/s1600/Grapevinesnail_01.jpg)](https://4.bp.blogspot.com/-LEAcNfC4EmQ/VC1ySqlz7cI/AAAAAAAAEO4/yVEgs7T6jlo/s1600/Grapevinesnail_01.jpg)

After getting questions about it I recently added the [Slow Exit contribution](https://github.com/evennia/evennia/blob/master/contrib/slow_exit.py) to the main repository as an example.   
  
Delayed movement is something often seen in various text games, it simply means that the time to move from room to room is artificially extended.  
  
Evennia's default model uses traditional MU* rooms. These are simple nodes with exits linking them together. Such Rooms have no internal size and no inherent spatial relationship to each other. Moving from any Room to any other is happening as fast as the system can process the movement.  
  
Introducing a delay on exit traversal can have a surprisingly big effect on a game:  

-   It dramatically changes the "feel" of the game. It often makes the game feel less "twitch" and slows things down in a very real way. It lets Players consider movement as a "cost".
-   It simulates movement speed. A "quick" (or maybe well-rested) character might perceive an actual difference in traversal. The traversal speed can vary depending on if the Character is "running" or "walking".
-   It can emulate travel distance. An Exit leading to "the top of the mountain" may take longer to traverse than going "inside the tent".
-   It makes movement a "cost" to take into consideration in the game. Moving back and forth over and over across a distance of multiple rooms becomes a much more daunting prospect with a time delay than if you could just zip along as quickly as you could press the button. This also has effects on map and quest design.

Introducing delayed movement in Evennia is simple. But to explain the idea, let's first briefly explain how Evennia implements Exits.  
  

#### A brief sideline: About Exits

  
An Exit in Evennia is a persistent Object sitting in a room. The Exit class is just like any Object except for two things - it stores a "destination" property and it houses a CommandSet on itself. This particular CommandSet holds a single command with the same name as the Exit object.  
  
Commands and CommandSets are things [I've covered in earlier blog posts](http://evennia.blogspot.se/2012/08/taking-command.html). Suffice to say is that any number of command sets can be merged together dynamically to at any moment represent the commands available to the Character at any given time or situation.  
  
What happens when an Exit bject is in the same room as a Character is that the Exit's command set is dynamically merged with that of the Character. This means a new command - which always has the same name as the Exit - becomes available. The result is that if the Exit object is called "south", the Character can use the command "south". By default all the command does is to call a hook method on the Exit object. This hook hooks simply moves the calling Character to the "destination" stored by the Exit. Done!  
  
The nice thing with this is that the whole system is implemented without any special cases or custom hard-wired code. It also means that the entire Exit system can be changed and modified without ever touching Evennia's core.  
   

#### Delaying Exits

To delay the traversal, the principle is simple - after the Exit command has triggered, wait for a little while before continuing.  
  
Technically we define a new class of Exit, let's call it SlowExit, inheriting from the default Exit. We locate the spot where the Exit normally sends traversing objects on their way (this is a method called move_to()).  
  
Since Evennia is based on Twisted, we use Twisted's intrinsic CallLater() function to delay the move for as many seconds we desire (in the contrib I use a thin wrapper around CallLater called delay()). The result is that the command is called, you get a little text saying that you have started moving ... and a few seconds later you actually move.  
  
Once one understands how Exits work it's really quite straight forward - see the [code on github](https://github.com/evennia/evennia/blob/master/contrib/slow_exit.py) for more details (it's got plenty of comments).  
  
In the contrib are also some example utility commands for setting one's movement speed and to abort movement if you change your mind before the timeout has passed.  
  
This simple start can easily be expanded as befits each individual game. One can imagine introducing anything from stamina costs to make travel time be dynamically calculated based on terrain or other factors.