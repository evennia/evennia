[prev lesson](./Starting-Part2) | [next lesson](./Game-Planning)

# Where do I begin? 

The good news is that following this Starting tutorial is a great way to begin making an Evennia game. 

The bad news is that everyone's different and when it comes to starting your own game there is no 
one-size-fits-all answer. Instead we will ask a series of questions 
to help you figure this out for yourself. It will also help you evaluate your own skills and maybe 
put some more realistic limits on how fast you can achieve your goals. 

> The questions in this lesson do not really apply to our tutorial game since we know we are doing it 
> to learn Evennia. If you just want to follow along with the technical bits you can skip this lesson and 
> come back later when you feel ready to take on making your own game.

## What is your motivation for doing this?

So you want to make a game. First you need to make a few things clear to yourself.

Making a multiplayer online game is a _big_ undertaking. You will (if you are like most of us) be
doing it as a hobby, without getting paid. And you’ll be doing it for a long time.

So the very first thing you should ask yourself (and your team, if you have any) is 
_why am I doing this_? Do some soul-searching here. Here are some possible answers:

- I want to earn recognition and fame from my online community and/or among my friends.
- I want to build the game so I can play and enjoy it myself.
- I want to build the same game I already play but without the bad people.
- I want to create a game so that I can control it and be the head honcho.
- A friend or online acquaintance talked me into working on it.
- I work on this because I’m paid to (wow!)
- I only build this for my own benefit or to see if I can pull it off.
- I want to create something to give back to the community I love.
- I want to use this project as a stepping-stone towards other projects (like a career in game design
or programming).
- I am interested in coding or server and network architectures, making a MUD just seems to be a good
way to teach myself.
- I want to build a commercial game and earn money.
- I want to fulfill a life-long dream of game making.

There are many other possibilities. How “solid” your answer is for a long-term development project
is up to you. The important point is that you ask yourself the question.

**Help someone else instead** - Maybe you should _not_ start a new project - maybe you're better off
helping someone else or improve on something that already exists. Or maybe you find you are more of a 
game engine developer than a game designer. 

**Driven by emotion** - Some answers may suggest that you are driven by emotions of revenge or disconcert. Be careful with that and
check so that's not your _only_ driving force. Those emotions may have abated later when the project 
most needs your enthusiasm and motivation.

**Going commercial** - If your aim is to earn money, your design goals will likely be very different from 
those of a person who only creates as a hobby or for their own benefit. You may also have a much stricter
timeline for release. 

Whichever your motivation, you should at least have it clear in your own mind. It’s worth to make
sure your eventual team is on the same page too.

## What are your skills?

Once you have your motivations straight you need to take a stock of your own skills and the skills
available in your team, if you have any.

Your game will have two principal components and you will need skills to cater for both:

- The game engine / code base - Evennia in this case. 
- The assets created for using the game engine (“the game world”)

###  The game engine

The game engine is maintained and modified by programmers (coders). It represents the infrastructure
that runs the game - the network code, the protocol support, the handling of commands, scripting and
data storage.

If you are just evaluating Evennia, it's worth to do the following:

- Hang out in the community/forums/chat. Expect to need to ask a lot of “stupid” questions as you start 
developing (hint: no question is stupid). Is this a community in which you would feel comfortable doing so?
- Keep tabs on the manual (you're already here).
- How's your Python skills? What are the skills in your team? Do you or your team already know it or are 
you willing to learn? Learning the language as you go is not too unusual with Evennia devs, but expect it 
to add development time. You will also be worse at predicting how 'hard' something is to do. 
- If you don’t know Python, you should have gotten a few tastes from the first part of this tutorial. But 
expect to have to refer to external online tutorials - there are many details of Python that will not be 
covered.

### Asset creation

Compared to the level of work needed to produce professional graphics for an MMORPG, detailed text
assets for a mud are cheap to create. This is one of the many reasons muds are so well suited for a
small team.

This is not to say that making “professional” text content is easy though. Knowing how to write
imaginative and grammatically correct prose is only the minimal starting requirement. A good asset-
creator (traditionally called a “builder”) must also be able to utilize the tools of the game engine
to its fullest in order to script events, make quests, triggers and interactive, interesting
environments.

Assuming you are not coding all alone, your team’s in-house builders will be the first ones to actually 
“use” your game framework and build tools. They will stumble on all the bugs. This means that you 
need people who are just not “artsy” or “good with words”. Assuming coders and builders are not the 
same people (common for early testing), builders need to be able to collaborate well and give clear 
and concise feedback. 

If you know your builders are not tech-savvy, you may need to spend more time making easier 
build-tools and commands for them. 

## So, where do I begin, then?

Right, after all this soul-searching and skill-inventory-checking, let’s go back to the original
question. And maybe you’ll find that you have a better feeling for the answer yourself already:

- Keep following this tutorial and spend the time 
  to really understand what is happening in the examples. Not only will this give you a better idea
  of how parts hang together, it may also give you ideas for what is possible. Maybe something 
  is easier than you expected! 
- Introduce yourself in the IRC/Discord chat and don't be shy to ask questions as you go through
  the tutorial. Don't get hung up on trying to resolve something that a seasoned Evennia dev may 
  clear up for you in five minutes. Also, not all errors are your faults - it's possible the 
  tutorial is unclear or has bugs, asking will quickly bring those problems to light, if so.
- If Python is new to you, you should complement the tutorial with third-party Python references 
  so you can read, understand and replicate example code without being completely in the dark.
  
Once you are out of the starting tutorial, you'll be off to do your own thing.
  
- The starting tutorial cannot cover everything. Skim through the [Evennia docs](../../../index).
  Even if you don't read everything, it gives you a feeling for what's available should you need
  to look for something later. Make sure to use the search function.
- You can now start by expanding on the tutorial-game we will have created. In the last part there 
  there will be a list of possible future projects you could take on. Working on your own, without help
  from a tutorial is the next step.

As for your builders, they can start getting familiar with Evennia's default build commands ... but
keep in mind that your game is not yet built! Don't set your builders off on creating large zone projects.
If they build anything at all, it should be small test areas to agree on a homogenous form, mood
and literary style. 

## Conclusions

Remember that what kills a hobby game project will usually be your own lack of
motivation. So do whatever you can to keep that motivation burning strong! Even if it means
deviating from what you read in a tutorial like this one. Just get that game out there, whichever way
works best for you.

In the next lesson we'll go through some of the technical questions you need to consider. This should 
hopefully help you figure out more about the game you want to make. In the lesson following that we'll 
then try to answer those questions for the sake of creating our little tutorial game.

[prev lesson](./Starting-Part2) | [next lesson](./Game-Planning)