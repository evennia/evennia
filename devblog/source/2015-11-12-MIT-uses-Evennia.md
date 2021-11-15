title: MIT uses Evennia! 
copyrights: Image: MIT news

---

[![](https://2.bp.blogspot.com/-FPg1PS8At3k/VkR7vqSz1LI/AAAAAAAAEco/bKSpvhDxLp0/s320/MIT-Language-Games_0.jpg)](https://2.bp.blogspot.com/-FPg1PS8At3k/VkR7vqSz1LI/AAAAAAAAEco/bKSpvhDxLp0/s1600/MIT-Language-Games_0.jpg)

[](https://www.blogger.com/)Evennia was recently used as a test bed to train an AI system to attempt to play a MUD as a human would - by only reading and understanding the text on the screen.  
  
Researchers at MIT (Massachusetts Institute of Technology) recently presented the paper _Language understanding for Text-based games using Deep reinforcement learning_ [(PDF)](https://arxiv.org/pdf/1506.08941.pdf) at a conference on natural language processing. A summary is in the [MIT press release](http://news.mit.edu/2015/learning-language-playing-computer-games-0924#_msocom_1).  
  
I was contacted by these fine folks some time ago so I knew they had plans to use Evennia for their research. It's great to see they now have an article out on it! Evennia devs are also mentioned in the acknowledgements - so something for the Evennia dev community to be proud of!   
  

### MUDs are tricky

The main complication for an AI playing a MUD is that the computer has no access to the actual game state but must try to surmise how well it's doing only from the text given (same as a human would). The researchers compare the results from a range of deep-learning neural network algorithm that they train to play.  
  
To test their AI, the researchers first used Evennia to build a simple training "Home World": a 4-room "house" where the simple goal is to find and eat an apple while refraining to go to sleep. The room descriptions used here were pretty formulaic although not trivial to give a challenge. This they used to train their AI system.  
  
They then took this trained neural network and applied it to the real challenge, playing the Evennia [Tutorial World](https://github.com/evennia/evennia/wiki/Tutorial%20World%20Introduction). You can yourself try this out in our demo install or by just running a single command when starting Evennia. They call it "Fantasy World" in the article.  
  
The tutorial world has hand-written descriptions and often describes the exits as part of the room text. The article actually makes a comprehensive analysis of the tutorial world, including the available game states and transitions as well as the number of words and number of commands per state. Interesting stuff in itself. I presume the scientists have modified their copy of the tutorial world to provide better metrics for their analysis.  
  

### A bridge too far

As far as I understand from the article, the AI does understand to use commands with one or two arguments (like _eat apple_ or the _move red-root right_), but they note that actually finding the tomb of the fallen hero (the main quest of the tutorial) is too hard for the AI:  
  

> [...]However, this is a complex quest that requires the player to memorize game events and perform high-level planning which are beyond the scope of this current work.

So instead they evaluate the AI's performance on a more mundane task: Getting across the bridge to the castle. It's not clear to me if the AI actually plays more of the game too or if their test just exposes the AI to the bridge itself. I suspect it _does_ play more due to the examples they use from other rooms; evaluating the bridge-crossing is just a clear-cut metric to use for "success".  
  
The MIT press release claims that the AI is also scored on how much health/magic it has, but I don't see that mentioned in the article itself (and the tutorial world only has magic if you find the hero's tomb which they claim they cannot do).  
  
The bridge in Evennia's tutorial world is actually a single "room" that takes multiple steps to cross. At every step the room description changes to describe the progress. Random texts will appear as the bridge sways in the wind and various environmental cues are heard and seen. There is also a small chance of falling off the bridge if one lingers too long on it.  
  
So although all you really need to do is to walk east repeatedly, I can see why this can be a challenge to a neural network having no mental image of what a bridge is. It can only work off the text it's given at any given time.  
  
In the paper, the algorithms are evaluated both on their ability to actually cross the bridge and on how optimal their solution was, for example by not issuing invalid commands to the situation.  
  

### Beyond the bridge

The results are that after being trained on the training house setup, the AI _will_ eventually be able to cross the bridge. The particular algorithm proposed also perform slightly better than the comparison ones (and _a lot_ better than simple randomness).  
  
So from the perspective of the researchers this seems to be a success. Even so, this reinforces the fact that quite some way to go before an AI can *actually* play a real MUD successfully. Using MUDs for this type of research is a good idea though, and I do hope they expand and continue this line work in the future.  
  
Who knows, maybe the AI will even find that ancient tomb eventually!  