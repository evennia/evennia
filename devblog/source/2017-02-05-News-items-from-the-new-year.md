[![](https://cloud.githubusercontent.com/assets/294267/22219746/511151f8-e1ac-11e6-8445-9cdfd4b9ab5d.png)](https://cloud.githubusercontent.com/assets/294267/22219746/511151f8-e1ac-11e6-8445-9cdfd4b9ab5d.png)

The last few months have been mostly occupied with fixing bugs and straightening out usage quirks as more and more people take Evennia through its paces.  
  
## Webclient progress  
  
One of our contributors, mewser/titeuf87 has put in work on implementing part of our roadmap for the webclient. In the first merged batch, the client now has an option window for adjusting and saving settings. This is an important first step towards expanding the client's functionality. Other  features is showing help in an (optional) popup window and to report window activity by popup and/or sound.  
  
The goal for the future is to allow the user or developer to split the client window into panes to which they can then direct various output from the server as they please It's early days still but some of the example designs being discussed can be found in the [wiki webclient brainstorm](https://github.com/evennia/evennia/wiki/Webclient%20brainstorm) (see the title image of this blog for one of the mockups).  
   
## New server stuff  
  
Last year saw the death of our old demo server on horizondark.com, luckily the new one at [silvren.com](http://silvren.com:4281/) has worked out fine with no hickups. As part of setting that up, we also got together a more proper list of recommended hosts for Evennia games. Evennia requires more memory than your average C code base so this is important information to have. It seems most of our users run Evennia on various cloud hosting services rather than from a traditional remote server login.  
  
## Arx going strong   
  
The currently largest Evennia game, the mush [Arx - After the Reckoning](http://play.arxmush.org/) has helped a lot in stress testing. Their lead coder Tehom has also been active both in reporting issues and fixing them - kudos! There are however [some lingering issues](https://github.com/evennia/evennia/issues?utf8=%E2%9C%93&q=is%3Aopen%20is%3Aissue%20author%3ATehomCD%20label%3Abug) which appears rarely enough that they have not been possible to reproduce yet; we're working on those. Overall though I must say that considering how active Arx is, I would have expected to have seen even more "childhood diseases" than we have.   
  
## Launch scripts and discussions  
  
It is always interesting with feedback, and some time back another discussion thread erupted over on [musoapbox, here](http://musoapbox.net/topic/1366/what-is-out-there-hard-and-soft-codebases-of-choice). The musoapbox regulars have strong opinions about many things and this time some were critical of Evennia's install process. They felt it was too elaborate with too many steps, especially if you are approaching the system with no knowledge about Python. Apparently the average MUSH server has a much shorter path to go (even though that does require C compiling). Whereas I don't necessarily agree with all notions in that thread, it's valuable feedback - I've long acknowledged that it's hard to know just what is hard or not for a beginner.  
  
Whereas we are planning to eventually move Evennia to pypi (so you can do pip install evennia), the instructions around getting virtualenv setup is not likely to change. So there is now unix shell scripts supplied with the system for installing on debian-derived systems (Debian, Ubuntu, Mint etc). I also made scripts for automating the setup and launch of Evennia and to use it with linux' initd within the scope of a virtualenv.  
So far these scripts are not tested by enough people to warrant them being generally recommended, but if you are on a supported OS and is interested to try they are found from the top of the Evennia repo, in bin/unix/. More info can be found [on their documentation page](https://github.com/evennia/evennia/wiki/Start-Stop-Reload#optional-server-startup-script-linux-only).  
  
## Docker  
  
Speaking of installing, Evennia now has an official Docker image, courtesy of the work of contributor and Ainneve dev feend78. The image is automatically kept up-to.date with the latest Evennia repo and allows Evennia to be easily deployed in a production environment (most cloud services supports this). See [Docker wiki page](https://github.com/evennia/evennia/wiki/Running%20Evennia%20in%20Docker) for more info.  
  
  
## Lots of new PRs  
  
There was a whole slew of contributions waiting for me when returning from Chistmas break, and this has not slowed since. Github makes it easy to contribute and I think we are really starting to see this effect (Google Code back in the day was not as simple in this regard). The best thing with many of these PRs is that they address common things that people need to do but which could be made simpler or more flexible. It's hard to plan for all possibilities, so many people using the system is the best way to find such solutions.  
  
Apart from the map-creation contribs from last year we also have a new Wildnerness system by mewser/titeuf87. This implements wilderness according to an old idea I had on the mailing list - instead of making a room per location, players get a single room.  The room tracks its coordinate in the wildnerness and updates its description and exits dynamically every time you move. This way you could in principle have an infinite wilderness without it taking any space. It's great to see the idea turned into a practical implementation and that it seems to work so well. Will be fun to see what people can do with it in the future!