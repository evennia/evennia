[![](https://1.bp.blogspot.com/-GNQ1IGvFf3o/X44OC1-OxXI/AAAAAAAALgY/OugrLSGGW7YgPDxHuG-tveB-xcCQ2RVZACLcBGAsYHQ/s0/book.png)](https://1.bp.blogspot.com/-GNQ1IGvFf3o/X44OC1-OxXI/AAAAAAAALgY/OugrLSGGW7YgPDxHuG-tveB-xcCQ2RVZACLcBGAsYHQ/s207/book.png)

Last post I wrote about the upcoming v1.0 of Evennia, the Python MU* creation engine. We are not getting to that 1.0 version quite yet though: The next release will be 0.9.5, hopefully out relatively soon (TM).  

Evennia 0.9.5 is, as you may guess, an intermediary release. Apart from the 1.0 roadmap just not being done yet, there is one other big reason for this - we are introducing documentation versioning and for that a proper release is needed as a base to start from. Version 0.9.5 contains everything already in _master_ branch, so if you have kept up-to-date you won't notice too much difference. Here are some highlights compared to version 0.9:

-   EvMore will paginate and properly handle both EvTables and database query output. For huge data sets, pagination can give a 100-fold speed-increase. This is noticeable e.g. in the **scripts** and **spawn/list** commands, once you have a lot of items.
-   EvMenu templating language, to make it easier to create simpler menus. 
-   Webclient improvements: Cleanup of interface and the ability for players to save/load their pane layouts from the client. The developer can still provide a default for them to start out with.  
    
-   MUD/Evennia Intro wizard to the tutorial world to explain basic game controls in an interactive way. 
-   Default channels can now be defined in settings instead of having to do so from in-game.   
    
-   New documentation system (see below).  
    
-   Many, many bug fixes and optimizations!

Many contributors helped out along the way. See the [changelog](https://github.com/evennia/evennia/blob/master/CHANGELOG.md) where contributors of the bigger new features are listed.  

## The path to a new documentation

For many years we've used the Github wiki as our documentation hub. It has served us well. But as mentioned [in my previous post](http://evennia.blogspot.com/2020/04/spring-updates-while-trying-to-stay.html), it has its drawbacks, in particular when it comes to handling documentation for multiple Evennia versions in parallel.

After considering a bunch of options, I eventually went with [sphinx](https://www.sphinx-doc.org), because it has such a good autodoc functionality (parsing of the source-code docstrings). This is despite our wiki docs are all in markdown and I dislike restructured text quite a bit. Our code also uses friendly and in-code-readable Google-style docstrings instead of Sphinx' hideous and unreadable format. 

Luckily there are extensions for Sphinx to handle this: 

-   [Napoleon](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html) to convert Google-style docstrings to reST on the fly
-   [recommonmark](https://recommonmark.readthedocs.io/en/latest/index.html) to convert our markdown wiki pages to reST on compile-time  
    
-   [sphinx-multiversion](https://holzhaus.github.io/sphinx-multiversion/master/index.html) to merge docs from one or more GIT branches into a documentation where you can select between the versions.  
    

What could go wrong? Well, it's been quite a ride.

#### Getting Markdown into reST  

Linking to things in recommonmark turned out to be very flaky. I ended up forking and merging a bunch of PRs from the project but that was not enough: Clearly this thing was not built to convert 200 pages of technical markdown from a github wiki.

My custom fork of recommonmark had to be tweaked a bit for my needs, such as not having to specify the **.md** file ending in every link and make sure the url-resolver worked as I expected. There were a bunch of other things but I will probably not merge this back, the changes are pretty Evennia-specific.  

Even so, many of my wiki links just wouldn't work. This is not necessarily recommonmark's fault, but how sphinx works by grouping things into _toctrees_, something that the Evennia wiki doesn't have. 

Also, the recommonmark way to make a toctree in Markdown is to make a list of links - you can't have any descriptive text, making the listing quite useless (apparently people only want bland lists of link-names?). After trying to figure out a way to make this work I eventually capitulated - I make pretty lists in Markdown while using a "hidden" toctree to inform sphinx how the pages are related.  

#### Getting the wiki into the new doc site  

This required more custom code. I wrote a custom importer that reads the wiki and cleans/reformats it in places where recommonmark just dies on them. I also made a preprocessor that not only finds orphan pages but also builds a toctree and remaps all links in all documents to their actual location on compilation. The remapper makes it a lot easier to move things around. The drawback is that every page needs to be uniquely named. Since this was already the case in the wiki, this was a good tradeoff. So with a lot of custom code the wiki eventually could port automatically.   

The thing is, that even with all this processing, recommonmark doesn't support stuff like Markdown tables, so you still have to fall back to reST notation for those. And Napoleon, while doing a good job of parsing google docstrings, do _not_ expect Markdown. So the end result is _mostly_ markdown but we still have to fall back to reST for some things. It's probably as far as we get.  

#### Deploying the docs   

Figuring out how to build and deploy these components together was the next challenge. Sphinx' default Makefile was quite anemic and I also wanted something that regular contributors could use to test their documentation contributions easily. I ended up having to expand the Makefile quite a lot while also adding separate deploy scripts and interfaces to github actions (which we recently started using too).

Finally, the versioning. The sphinx-multiversion plugin works by extracting the branches you choose from git and running the sphinx compiler in each branch.  The plugin initially had a bug with how our docs are located (not at the root of the package) but after I reported it, it was quickly fixed. The result is a static document site where you can select between the available versions in the sidebar.

I've not gotten down to trying to make LaTeX/PDF generation work yet. I'm dreading it quite a bit...   

#### Where we are  

The github wiki is now closed for external contributions. The v0.9.5 of the new documentation will pretty much be an import of the last state of the wiki with some minor cleanup (such as tables). While we'll fix outright errors in it, I don't plan to do many fixes of purely visual glitches from the conversion - the old wiki is still there should that be a problem.  

The main refactoring and cleanup of the documentation to fit its new home will instead happen in v1.0. While the rough structure of this is already in place, it's very much a work in progress at this point.

#### Conclusions

Evennia 0.9.5 has a lot of features, but the biggest things are 'meta' changes in the project itself. After it is out, it's onward towards 1.0 again!