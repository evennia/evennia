[![](https://3.bp.blogspot.com/-63mc2ur3Gyk/Wmz6puNzMGI/AAAAAAAAH94/vsXKZcCu2MwKlEaoCi7IjzWHJnPvGAQKgCLcBGAs/s200/karate-312470_640.png)](https://3.bp.blogspot.com/-63mc2ur3Gyk/Wmz6puNzMGI/AAAAAAAAH94/vsXKZcCu2MwKlEaoCi7IjzWHJnPvGAQKgCLcBGAs/s1600/karate-312470_640.png)

The last few weeks I have reworked the way [Evennia](http://www.evennia.com/)'s startup procedure works. This is now finished in the _develop_ branch so I thought I'd mention a little what's going on.  
  
Evennia, being a server for creating and running text-games (MU*s), consists of two main processes:  

-   The _Portal_ - this is what players connect to with their clients.
-   The _Server_ - this is the actual game, with the database etc. This can be shutdown and started again without anyone connected to the Portal getting kicked from the game. This allows for hot-adding new Python code into the running Server without any downtime. 

Since Evennia should be easy to set up _and_ also run easily on Windows as well as on Linux/Mac, we have foregone using the linux process management services but instead offered our own solution. This is how the reload mechanism currently looks in master branch:  
  

[![](https://1.bp.blogspot.com/-U98LnVTJF7Y/WmzvHbQN2NI/AAAAAAAAH9U/10u8n91y56MdyW4Fmuv9k5Abk79TCCtUgCLcBGAs/s400/portal_server_reboot_master.png)](https://1.bp.blogspot.com/-U98LnVTJF7Y/WmzvHbQN2NI/AAAAAAAAH9U/10u8n91y56MdyW4Fmuv9k5Abk79TCCtUgCLcBGAs/s1600/portal_server_reboot_master.png)

Here I've excluded connections irrelevant to reloading, such as the Twisted AMP connection between Portal and Server. Dashed lines suggest a more "temporary" connection than a solid line.  
  
The **_Launcher_** is the evennia program one uses to interact with the Server in the terminal/console. You give it commands like evennia start/stop/reload.  
  

-   When **starting**, the Launcher spawns a new program, the _**Runner**_, and then exits. The Runner stays up and starts the Portal and Server. When it starts the Server, it does so in a blocking way and sits waiting in a stalled loop for the Server process to end. As the Server and Portal start they record their current process-ids in _**.pid files**_. 
-   When **reloading**, the Launcher writes a flag in a little _**.restart**_ _**file**_. The Launcher then looks up the Server's .pid file and sends a SIGINT signal to that process to tell it to gracefully shut down. As the Server process dies, the Runner next looks at the Server's .restart file. If that indicates a reload is desired, The Runner steps in its loop and starts up a new Server process. 
-   When **stopping,** everything happens like when reloading, except the .restart file tells the Runner that it should just exit the loop and let the Server stay down. The Launcher also looks at the Portal's .pid file and sends a SIGINT signal to kill it. Internally the processes catch the SIGINT and close gracefully.

The original reason for this Server-Portal-Runner setup is that the Portal is _also_ reloadable in the same way (it's not shown above). But over time I've found that having the Portal reloadable is not very useful - since players get disconnected when the Portal reloads one can just as well stop and start both processes. There are also a few issues with the setup, such as the .pid files going stale if the server is killed in some catastrophic way and various issues with reliably sending signals under Windows. Also, the interactive mode works a little strangely since closing the terminal will actually kill the Runner, not the Server/Portal - so they will keep on running except they can no longer reload ...  
It overall feels a little ... fiddly.  
  
In develop branch, this is now the new process management setup:  
  

[![](https://4.bp.blogspot.com/-R0ziGF8cMPc/Wmz0ppbJkQI/AAAAAAAAH9o/2BNcUTEqvBwkmlZAy7Q74Xmww_LkpB3wgCLcBGAs/s400/portal_server_reboot_develop.png)](https://4.bp.blogspot.com/-R0ziGF8cMPc/Wmz0ppbJkQI/AAAAAAAAH9o/2BNcUTEqvBwkmlZAy7Q74Xmww_LkpB3wgCLcBGAs/s1600/portal_server_reboot_develop.png)

  
The Portal is now a Twisted [AMP](https://twistedmatrix.com/documents/current/api/twisted.protocols.amp.html) server, while the Evennia Server and Launcher are AMP clients. The Runner is no more.  
  

-   When **starting**, the Launcher spawns the Portal and tries to connect to it as an AMP client as soon as it can. The Portal in turn spawns the Server. When the Server AMP client connects back to the Portal, the Portal reports back to the Launcher over the AMP connection. The Launcher then prints to the user and disconnects. 
-   When **reloading**, the Launcher connects to the Portal and gives it a reload-command. The Portal then tells the Server (over their AMP connection) to shutdown. Once the Portal sees that the Server has disconnected, it spawns a new Server. Since the Portal itself knows if a reload or shutdown is desired no external .restart (or .pid) files are needed. It reports the status back to the Launcher that can then disconnect.
-   When **stopping**, the Launcher sends the "Stop Server" command to the Portal. The Portal tells the Server to shut down and when it has done so it reports back to the Launcher that the Server has stopped. The Launcher then sends the "Stop Portal" command to also stop the Portal.  The Launcher waits until the Portal's AMP port dies, at which point it reports the shutdown to the user and stops itself.

So far I really like how this new setup works and while there were some initial issues on Windows (spawning new processes does not quite work they way you expect on that platform) I think this should conceptually be more OS-agnostic than sending kill-signals.   
  
This solution gives much more control over the processes. It's easy to start/stop the Server behind the portal at will. The Portal knows the Server state and stores the executable-string needed to start the Server. Thus the Server can also itself request to be reloaded by just mimicking the Launcher's instructions.  
 The launcher is now only a client connecting to a port, so one difference with this setup is that there is no more 'interactive' mode - that is the Server/Portal will always run as daemons rather than giving log messages directly in the terminal/console. For that reason the Launcher instead has an in-built log-tailing mechanism now. With this the launcher will combine the server/portal logs and print them in real time to easily see errors etc during development.  
  
The merger of the develop branch is still a good bit off, but anyone may try it out already here: https://github.com/evennia/evennia/tree/develop . Report problems to the issue tracker as usual.