[![](https://1.bp.blogspot.com/-O_mHSjm4u90/UvVmXrY3kkI/AAAAAAAACJc/5bREd9YEbLU/s1600/ar12943602961303.jpg)](https://1.bp.blogspot.com/-O_mHSjm4u90/UvVmXrY3kkI/AAAAAAAACJc/5bREd9YEbLU/s1600/ar12943602961303.jpg)

A few weeks back, the Evennia project made the leap from Google Code to GitHub ([here](https://github.com/evennia/evennia)). Things have been calming down so it's time to give a summary of how the process went.  
  
Firstly I want to say that I liked Google Code. It did everything expected of it with little hassle. It had a very good Issue system (better than GitHub in my opinion) and it allowed us to use Mercurial instead of Git for version control (I just happen to like Mercurial better than Git, so sue me). Now, GitHub is getting to be something of a standard these days. But whereas our users have occationaly inquired about us making the move, I've been reluctant to do so.   
  
The problem I _did_ have with Google Code was that I got the increasing feeling that Google didn't care all that much about it. It worked decently, but it was not really going anywhere either. What finally made me change my mind though was an event just after summer last year. There was a bug in Google Code that made the links to online clones disappear. It was worse than that - creating new online clones of the main repo didn't work - people wanting to contribute using a clone just couldn't.   
  
This is extremely critical functionality for a code-sharing website to have! I made a bug report and many other projects chimed in seeing the same issues. Eventually the links returned and everything worked the way it had. But it took _several months_ before this critical bug was fixed. Even then Google didn't even bother to close my issue. This suggested quite strongly to me that Google Code is not really a priority even for its parent company. It was time to consider a move.  
  
I was never personally a fan of Git. It is undoubtedly powerful, but I always felt its syntax way too archaic and the number of ways to shoot yourself in the foot way too many. But I do like GitHub better than BitBucket (I've used both in other projects), so that's where we nevertheless were heading.  
  
Already last year I created an Evennia "organization" on GitHub and one of our  users first helped to set up a Git Mirror of our Mercurial repo. The idea was a good one - have a mirror on GitHub, allowing the transition to be more gradual. In the end this didn't work out though - there were some issue with the hg-git conversion and the mirror never didn't actually update. When I checked back and it was three months behind we just removed that first ill-fated version.   
  
In the end I decided to not fiddle about with it, but to move everything over in one go.  
  

###  Converting the repository

I set aside a new folder on my hard drive and cloned the original mercurial repo into a new sub folder. A good idea is to set up a quick Python [virtual environment](https://pypi.python.org/pypi/virtualenv) for easily getting updated dependencies of build scripts.   
  
I initialized an empty Git repository and used a program called [hg-fast-export](https://github.com/frej/fast-export) to convert. As it turned out there were some finer details to consider when doing that:  
  

-   The most obvious one was that the conversion initially failed, complaining about the Mercurial original containing "unnamed branches". These came from a contributor who did _something_ to spawn off all sorts of weird branches with little purpose. I should not have merged those into main in the first place, but in those days I didn't know mercurial well enough to be  concerned. In the end I simply used mercurial's MQ extension to remove the unnamed (and unused) branches so the conversion could complete.
-   The second issue was that Mercurial is less stringent about its author strings than Git is. Git's author string is "name <email>". Over the years we have gotten contributions from people with all sorts of combinations of names, with or without an email address. So for this we had to supply a mapping file to the converter. It's basically a list of old_author_string = new_author_string and allows for grouping the various used names as needed (some of them were the same person using slightly different author strings). 

  
Once this was in place, the repo conversion worked fine. It was just a matter of changing the .hgignore file to a .gitignore file and change some code that made use of mercurial to get and display the current revision id.  

###  Converting the Wiki, part one

  
Evennia's wiki consitutes our documentation, it's some 80+ pages or so by now. Definitely not something we want to loose. Google Code use a dialect of MediaWiki whereas GitHub's wiki supports a few other formats, like markdown or reST. I needed to convert between them.  
  
Digging around a bit I found [googlecode2github](https://github.com/trentm/googlecode2github.git). This download contains python scripts for converting the wiki as well as Issues. I didn't really get the issues-converter to work, so I had to find another solution for that (see next section).  
  
All in all, the initial wiki conversion worked decently - all the pages were converted over and were readable. I was even to the point of declaring success when finding the damn thing messed up the links. Googe Code writes links like this: [MyLink Text to see on page]. The script converted this to [[MyLink|Text to see on page]]. Which may look fine except it isn't. GitHub actually wants the syntax in the inverse order: [[Text to see on page|MyLink]].  
  
Furthermore, in Google Code's wiki, code blocks were marked with  
  
```
{{{   
 <verbatim code>   
}}}
```
  
In markdown, code blocks are created just by indenting the block by four spaces. The converter dutifully did this - but it didn't add empty lines above and below the block, which is another thing markdown requires. The result was that all code ended up mixed into the running text output.  
  
I could have gone back and fixed the converter script, but I suspected there would be enough small things to fix anyway. So in the end I went through 80+ pages of fixing link syntax and adding empty lines by hand. After that I could finally push the first converted wiki version up to the GitHub wiki repository.  
  
Some time later I also found that there is a way to let GitHub wiki pages use syntax highlighting for the language of your choice. The way to do this is to enclose your code blocks like this:  
  
```` 
```python  
  
<verbatim code>  
  
``` 
````
  
This is apparently "GitHub-flavoured" markdown. So another stint into all the pages followed, to update everything for prettiness.  
  

###  Converting Google Code Issues

  
I didn't want to loose our Issues from Google Code. I looked around a bit and tested some conversions for this (it helps to be able to create and delete repos on GitHub with abandon when things fail). I eventually settled on [google-code-issues-migrator](https://github.com/arthur-debert/google-code-issues-migrator).  
  
This is a Python script that gathers all the Issues from a given Google Code project. It then uses GitHub's API to re-post the issues. It retains the issue numbers and re-maps the Google Code Issue tags to GitHub's equivalent. It didn't retain most other formatting and whereas I ended up as the creator of all issues, the converter included the name of the original author as well as a link back to the original Google Code one. I found that to be quite sufficient for our needs.   
  

###  Converting the IRC announcer

  
A lot of development discussion goes on in our IRC channel #evennia on Freenode. There is an announcer bot in there that I've written, that collates information from various sources and reports it in the IRC channel:  
  
-   Repository updates
-   Wiki updates
-   Issue creation and updates
-   Mailing list/forum posts
-   Dev-blog updates (this blog)

  
Say what you will about Google, but they are great at offering RSS feeds to all their stuff. So my IRC bot was basically a glorified threaded RSS reader that echoed changes to the channel as they came in. This had been working nicely for years.  
  
GitHub does offer RSS feeds to -some- of their offerings, but it's a lot more patchy. I eventually had to do quite a bit of hacking to get everything reporting the way we were used to.  
  

-   GitHub has its own IRC announcer bot that reports to IRC. The problem is that this will connect, send message and then disconnect. This causes a lot of spam in the channel. We neither can nor want to set +n on our channel to allow external messages either. The way I solved this was to expand my own custom IRC bot to sit in _two_ irc channels. The GitHub announcer connects to only one of them (so this gets all the spammy connect messages). My IRC bot picks up the announcement and echoes it cleanly to our main #evennia channel.  It works really well.
-   Issues are handled by the GitHub announcer in the same way. 
-   GitHub has no automatic way to report wiki updates. It doesn't even have a proper RSS feed. However, a user clued me in on using the [pipes](http://pipes.yahoo.com/pipes/pipe.info?_id=02bfefe73ba14054570ce82f1929e433) website to relay an RSS feed from github. I then configured my IRC bot to check that RSS and report it (I also changed the IRC colours to match the GitHub-announcer ones).
-   Mailing list and blog haven't changed, so those are still handled via RSS as before.

  
All this done, the modified IRC announcement works well.  
  

###  Closing the book on Google Code

  
At this point all the critical things were moved over. So after some heads-up warnings on the mailing list (and users helping to rewrite our documentation to use Git instead of mercurial) we eventually made the official move.  
  
One thing I really dislike is when a project switches hosts and don't let users know about it in their revision history. So I made a mercurial-only last commit announcing that the repo is closed and giving the link to the new one.  
  
The Google Code page doesn't go anywhere, but I changed the front page to point to GitHub instead. I even made an issue in the Issue tracker with a title telling people not to use that tracker anymore. Finally I re-pointed all the links on [http://www.evennia.com](http://www.evennia.com/) to GitHub and made a mailing list posting. Move was officially complete.  
  

###  Converting the Wiki, part 2

  
At this point were were officially moved over and I started to look into getting fancy with our documentation. We have for the longest time made automated translations of our wiki for compiling by [ReadTheDocs](https://readthedocs.org/projects/evennia/).  
  
Getting Google Code's special wikimedia syntax into reST (that ReadTheDocs uses) used to mean jumping through a few hoops. My hackish solution worked in two steps. First a custom python script (whose originating url I can no longer find, sorry) converted the Google Code wiki to HTML. Once this was done, [pandoc](http://johnmacfarlane.net/pandoc/) converted the files from HTML to reST. The result was ... acceptable. There were some minor issues here and there but mostly the result was readable.  
  
I figured that converting from the more standard Markdown of the GitHub wiki to reST should be a breeze by comparison. Not so.  
  
The first hurdle was that the version of pandoc coming with my Linux distribution was too old to support Github-flavoured markdown syntax. I knew from before that Pandoc worked so I didn't want to start with something else. I had to download the several hundred MBs needed by the Haskell build environment and their package manager in order to get and compile all the dependencies and finally the latest version of pandoc. To their credit it was all a very streamlined experience, it just took quite some time.  
  
The second hurdle came when finally looping pandoc to convert all wiki files. It turns out to be that the [[Text on page|address]] syntax I had manually corrected earlier is a special syntax offered by _Gollum,_ the engine powering GitHub's wiki behind the scenes. None of the markdown-to-reSt converters I looked at (pandoc or otherwise) even recognized this syntax as a link at all. As it turns out, normal markdown actually expects its links in the format [Text on page](address).  
  
I was not going to go through and edit all those pages _again._ So my next step was to write a script to scan and replace all the [[...|...]] syntax in our wiki and replace it with the standard markdown one. After this the markdown files converted to reST quite nicely -- formatting-wise they look much better than the old wiki to HTML to reST chain I had to use from Google Code.  
  
Problem was that when compiling these reST pages into HTML with Sphinx, no links worked.  
  
Each individual page looked okay, just that the links were not pointing to anything reasonable. In retrospect this was not so strange. Pandoc knows nothing about the relationships between files, and clearly the simple naming scheme used for addresses is something the wiki softwares knows and Sphinx does not.  
  
Some thinking lead to a custom Python script for renaming the link targets in the converted pages to their html page name. This needed to handle the fact that wiki links also allows whitespace. So the [Start](Getting Started) link would be converted to [Start](GettingStarted.html), which seems to be the format with which Sphinx will generate its pages.  
  
One also needs to have a "toc" (Table of Contents) to tie all those pages together for the benefit of Sphinx. I just used a "hidden" toc, letting my converter script add this to the bottom of my normal index file. As long as it's included _somewhere,_ Sphinx will be happy.  
  
Originally I put the reST files in a subfolder of the GitHub wiki repo, I thought I could just point ReadTheDocs to that repo later. The GitHub wiki has a strange "feature" though. It seems to pick its wiki pages from _wherever_ they are in the repo, no matter if they are in the root or in subfolders. Suddenly I was starting to see reST-style pages appear in the online wiki, and sometimes I would get the markdown version (the two would go out of sync). Very strange and confusing.  
  
Since the files clearly "polluted" our wiki, I had to move the converted reST files to a separate branch of the wiki repository. This has the advantage of keeping all the support scripts and converter mechanisms separate from the normal wiki content. ReadTheDocs can luckily be set to read its information from another branch than master, so finally the latest converted wiki can again be read there!  
  
That concludes what I think was the last main conversion effort. Phew!  
  

###  Impressions so far

  
GitHub is nice. The merge requests and easy way to comment on them are really good. Since people are more familiar with using GitHub overall, it does seem to be a shorter step for people to make a fork and contribute small things. Doing the same in Google Code was probably not harder per se, just something less people were previously familiar with.  
  
Due to the modular way Evennia is structured, people are recommended to make a fresh clone of the new Git repo and simply copy their plugin source files and database back into it. So far this seems to have gone smoothly.  
  
The GitHub issue tracker is worse than the Google Code one. It has no good way to order Issues or list them in a more compact form (nor in a matrix). Not having good issue templates is really limiting; having to reply to issues only to ask for basic info they should include in their issue is an unnecessary time sink.  
  
I also find that there is no clear way to announce an issue change (like "Needing more information"). Tags work partly for this, but setting them is not announced anywhere as far as I can tell - they are just there.  
  
Most things also takes so much spaaace. Overall GitHub seems designed for people with big monitors. I have those, but most of the time I prefer working on my laptop. I'm sure it's a matter of habit, but Google Code is very compact by comparison. It gave a lot better overview of things. On GitHub I have to scroll everywhere and this is true both in the repo view, wiki and issues.  
  
These small quips nonwithstanding, I think this move will serve us well. There is a good wibe of development and continuing improvement going on at GitHub. There's plenty of help and tutorials all over. Since so many people are using GitHub, problems are more likely to have been answered before. And of course we hope this will in effect help more people find Evennia and join the fun.