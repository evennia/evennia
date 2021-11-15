[![](https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/DrinkingStraws.jpg/401px-DrinkingStraws.jpg)](https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/DrinkingStraws.jpg/401px-DrinkingStraws.jpg)

Recently, a user reported a noticeable delay between sending a command in-game to multiple users and the result of that command appearing to everyone. You didn't notice this when testing alone but I could confirm there was almost a second delay _sometimes_ between entering the command and some users seeing the result. A second is very long for stuff like this. Processing time for a single command is usually in the milliseconds. What was going on?  
  

### Some background 

Evennia has two components, the _Portal_ and the _Server,_ running as two separate processes_._ The basic principle is that players connecting to an Evennia instance connects to the Portal side - this is the outward facing part of Evennia. The connection data and any other input and output will be piped from the Portal to the Server and back again.  
  
The main reason for this setup is that it allows us to completely reset the Server component (reloading module data in memory is otherwise error-prone or at least very tricky to make generically work in Python) without anyone getting disconnected from the Portal. On the whole it works very well.  
  

### Debugging

  
Tracing of timings throughout the entire Server<->Portal pipeline quickly led me to rule out the command handler or any of the core systems being responsible - including both sides of the process divide was a few milliseconds. But in the _transfer_ between Portal and Server, an additional _900_ miliseconds were suddenly added! This was clearly the cause for the delay.  
  
Turns out that it all came down to faulty optimization. At some point I built a batch-send algorithm between the Server and Portal. The idea was to group command data together if they arrived too fast - bunch them together and send them as a single batch. In theory this would be more efficient once the rate of command sending increased. It was partly a DoS protection, partly a way to optimize transfer handling.  
  
The (faulty) idea was to drop incoming data into a queue and if the rate was too high, wait to empty that queue until a certain "command/per second" rate was fullfilled. There was also a timed routine that every second force-emptied the queue to make sure it would be cleaned up also if noone made any further commands.  
  
In retrospect it sounds silly but the "rate of command" was based on a simple two-time-points derivative;  
  

> rate = 1 / (now - last_command_time)

  
If this rate exceeded a set value, the batch queuing mechanism would kick in. The issue with this (which is easy to see now) is that if you set your limit at (say) 100 commands / second, two commands can happen to enter so close to each other time that their rate far exceed that limit just based on the time passed between them. But _there are not actually 100 commands coming in every second_ which is really what the mechanism was meant to react to.  
  
So basically using a moment-to-moment rate like this is just too noisy to be useful; the value will jump all over the place. The slowdown seen was basically the DoS protection kicking in because when you are relaying data to other users, each of them will receive "commands" in quick succession - fast enough to trigger the limiter. These would be routed to the queue and the sometimes-delay simply depended on  when the queue cleanup mechanism happened to kick in.  
  

### Resolution

  
Once having identfied the rate measuring bug, the obvious solution to this would be to gather command rates over a longer time period and take an average - you will then filter out the moment-to-moment noise and get an actually useful rate.  
  
Instead I ended up going with an even simpler solution: Every command that comes in ups a counter. If I want a command rate limit of 100 commands/second, I wait until that counter reaches 100. At that point I check when the time difference between now and when the counter was last reset. If this value is below 1, well then our command rate is higher than 100/second and I can kick in whatever queuing or limiter is needed. The drawback is that until you have 100 commands you won't know the rate. In practice though, once the rate is high enough to be of interest, this simple solution leads to an automatic check with minimal overhead.  
  
In the end I actually removed the batch-sending component completely and instead added command DoS protection higher up on the Portal side. The Command-input is now rate limited using the same count-until-limit mechanism. Seems to work fine. People have no artificial slowdowns anymore and the DoS limiter will only kick in at loads that are actually relevant. And so all was again well in Evennia world.