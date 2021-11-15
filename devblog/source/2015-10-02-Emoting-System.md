title: Emoting Systems, or how to chat up a girl
copyrights: Image: ©Griatch [deviantart](https://deviantart.com/griatch-art)

[![](https://lh6.googleusercontent.com/proxy/l_2MjemzGRtxOqicx4EXXRT63jmryGr7Ml_wvtSSDGg8Rc-oVzKL-_Jxy9f4gvkzROS3eE8jR3R9I2iguw0Cki4oc4reqwi607HGigS6iSO8BxHuZ53k70NUI0ZfWTpXoCqBm-Wr0LakUjfQQxIJIehaRGbvrvU=s0-d)](http://pre03.deviantart.net/54d0/th/pre/i/2012/114/c/8/what__s_yer_name__by_griatch_art-d4xfokb.jpg)

A few days ago I pushed an emoting contribution to Evennia. A "contrib" is an optional plugin system that is not part of core Evennia but is meant to be easily picked up and used in people's own designs.  
  
If you are not familiar with what an emoting system does, it is a way to decribe the actions of a character in the game. The simplest form of emote is a single command (like the command **dance** leading to some canned response, or in the case of a graphical game, a dance animation). This contribution offers a more sophisticated system though, allowing input like the following:  
  
emote /me smiles at /cheerful as he sits at her table. "Hello!" he says.  
  
Now, this includes /keywords that relate to the objects in the room. So assuming there is **_a very cheerful girl_** in the room, this string will come out as   
  
Griatch smiles at _**a very cheerful girl**_ as he sits at her table. **"Hello!"** he says.   
  
But she will actually see only my outward appearance (the short description) since she doesn't know me. So the cheerful girl (let's say her name is Sandra) would for example see  
  
_**A man in flowing robes**_ smiles at _**Sandra**_ as he sits at her table. **"Hello!"** he says.  
  
The emoting system has the following features:   
  

-   Short description replacement in emotes and in searches, as seen above. This means that you can do **look cute** and the system will know what you want to look at (in vanilla Evennia you'd need to use **look Sandra**).
-   Multi-word searching and disambiguation. If there is **a cute girl** and **a cute puppy** both in the same room, your referencing of /cute will  give an error listing the alternatives. You can then either include more words to make your reference unique or use an index (1-cute, 2-cute) to make it clear who you mean. This mimics normal object-key disambiguation in Evennia.
-   Recognition. You can assign your own aliases to people. If Sandra introduces herself you could assign her the name **Sandra** and henceforth be able to reference her as such and see that name appear. But you could also name her **The girl calling herself Sandra** if you didn't believe that's her actual name.
-   Languages. Everything within double-quotes is parsed as spoken language (like the Hello! above). By using writing this as **(elvish)"Hello!"**, this could be spoken in another language and those who don't speak elvish would receive an obfuscated string.
-   Masking. A person wearing a mask can force people's recognition replacement to deactivate so that they are not recognized anymore.

The emoting contrib comes as two files in evennia/contrib/: rpsystem.py and rplanguage.py. To use them fully, make your Characters and Rooms inherit from the supplied classes and/or add the new commands to the Character command set. Enjoy!  