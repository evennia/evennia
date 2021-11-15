copyrights: Image by [ryancr](https://www.flickr.com/photos/ryanr/142455033) (released under [Creative Commons](https://creativecommons.org/licenses/by-nc/2.0/))

---

[![](https://3.bp.blogspot.com/-wIhCzMzQyho/V3aDpCR8dEI/AAAAAAAAEog/L8_xmAiXKK8b-42Zoa7t8vjgpIBx1fgnQCLcB/s320/142455033_49ce50a89b_m.jpg)](https://3.bp.blogspot.com/-wIhCzMzQyho/V3aDpCR8dEI/AAAAAAAAEog/L8_xmAiXKK8b-42Zoa7t8vjgpIBx1fgnQCLcB/s1600/142455033_49ce50a89b_m.jpg)

In the month or so since the merger of Evennia's development branch and all its web-client updates, we have been in bug-fixing mode as more people use and stress the code.  
  
There have been some new features as well though - I thought it could be interesting to those of you not slavishly following the mailing list.  

### Shared web login

When you are logged into the website you will now also auto-login to your account in the web client - no need to re-enter the login information! The inverse is also true. You still need to connect to game at least once to create the account, but after that you will stay connected while the browser session lasts.  
  
Behind the scenes the shared login uses cookies linked to server-side Django sessions which is a robust and safe way to manage access tokens. Obviously browser sessions are irrelevant to telnet- or ssh connections.  
  

### Extended Nicks 

Evennia's nick(name) system is a way to create a personal alias for things in game - both to on-the-fly replacing text you input and for referring to in-game objects. In the old implementation this replacement was simply matched from the beginning of the input - if the string matched, it was replaced with the nick.  
  
In this new implementation, the matching part can be much more elaborate. For example you can catch arguments and put those arguments into the replacement nick in another order.  
  
Let's say we often use the @dig command this limited way:  
  
>  **@dig roomname;alias = exit;alias, backexit;alias**  
   
Let's say we find this syntax unintuitive. The new nick system allows to change this by catching the arguments in your nick and put it into the "real" command. Here is an example of a syntax putting the aliases in parentheses and separating all components with commas:  
  
**> nick newroom $1($2), $3($4), $5($6) = @dig $1;$2 = $3;$4, $5;$6**  
  
From here on you can now create your rooms with entries like this:   
  
**> newroom The great castle(castle), to the castle(castle), back to the path(back)**  
  

### Multidescer contrib

I have added a new "multidescer" to the contrib folder. A multidescer is (I think) a MUSH term for a mechanism managing more than one description. You can then combine any of these various descriptions into your "active" description.  
  
An example of usage:  
  
**desc hat = a blue hat.**  
**desc basic = This is a tall man with narrow features.**  
**desc clothing = He is wearing black, flowing robes.**  
  
 These commands store the description on the Character and references them as unique keywords. Next we can combine these strings together in any order to build the actual current description:   
  
**> desc/set basic + |/ + clothing + On his head he has + hat**  
**> look self**  
**This is a tall man with narrow features.**   
**He is wearing black, flowing robes. On his head he has a blue hat.**  
  
This allows for both very flexible and easy-to-update descriptions but also a way to handle freeform equipment and clothing. And you can of course use the nick system to pre-format the output  
  
**> nick setdesc $1 $2 $3 $4 = $1 + |/ + clothing + On his head he has a $4**  
  
This way you can clothe yourself in different outfits easily using the same output format:  
  
**> setdesc basic clothing hat**   
   
 The multidescer is a single, self-contained command that is easy to import and add to your game as needed.  
  
  
  
... There's also plenty of bug fixes, documentation work and other minor things or course.  
  
Anyway, summer is now upon us here in the northern hemisphere so things will calm down for a bit, at least from my end. Have a good 'un!  