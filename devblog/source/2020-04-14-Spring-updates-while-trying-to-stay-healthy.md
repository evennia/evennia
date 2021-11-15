copyrights: Image: ©George Hodan, released under CC0 Public Domain

--- 

[![](https://1.bp.blogspot.com/-vnauuJpCVfo/XpXkbERzSRI/AAAAAAAALJQ/lDoYHE6zjWsg7It_fsXn_3roGUISX2HxgCLcBGAsYHQ/s320/spring-flower-and-snow.jpg)](https://1.bp.blogspot.com/-vnauuJpCVfo/XpXkbERzSRI/AAAAAAAALJQ/lDoYHE6zjWsg7It_fsXn_3roGUISX2HxgCLcBGAsYHQ/s1600/spring-flower-and-snow.jpg)

So, spring grows nearer for those of us on the Northern hemisphere. With everyone hopefully hunkered down and safe from the Covid-19 pandemic, I thought it overdue to make another dev blog for the progress of Evennia, the Python MU*-creation system.  
  
  
The last few months have seen primarily bug fixing on the Evennia front, but it also has seen an uptick of PRs from the community and the re-opening of the develop branch in earnest. There is still quite a lot of work to do before we can add that extra 0.1 and go from version 0.9 to 1.0.  
  

### What's in a version?

  
For me personally, I never put much stock in the notion of versions. Evennia didn't even have versions until a few years back: We used to just have a rolling git release. But eventually it became clear that our user base was big enough that we needed to more clearly separate major (and possibly breaking) updates from what came before. So I started versioning at Evennia 0.5 and have had roughly a new release every year since (not a plan or a promise, it just happened to turn out that way).  
  
Evennia has been useful (and been used) for game development for many years already. But there is no denying that a 1.x label tends to convey more confidence in a system than a 0.x label, that's just the way things are. So while the new version is still quite some way off, there are a bunch of changes and improvements that we want to do in this release to mark the version change in a good way.  
  

### Documentation changes

  
Our documentation will move away from our trusty [Github wiki](https://github.com/evennia/evennia/wiki). Instead we will convert the wiki into a static github page built from sources inside evennia/docs/.  
  
The advantage of the wiki is that it is a very low entry for people to contribute and fix things using Github's editing system. We have had a lot of use of this over the years and the wiki has served us well. The drawbacks are starting to get ever more noticeable, however:  

-   Whereas the wiki is itself version-controlled, we cannot show multiple versions of the wiki at the same time. This makes it hard to update the documentation at the same time as non-released code is being written. This is probably my main reason for doing the change.
-   The wiki today consists of some 200+ pages. It is hard to get an overview of what is where and what needs to be updated. 
-   The wiki word-search functionality is not really great.
-   It's impossible to review changes before they go live, to check consistency and style. This has led to some documentation pages overlapping.
-   Building the documentation to local HTML or PDF is an archaic process that I doubt anyone but me has done with any regularity. 

The change so far planned is to switch to the [Sphinx](https://www.sphinx-doc.org/en/master/) documentation build-system (same as Python/Django etc is using). We will use it with extensions that allows us to still use Markdown like in the old wiki. This also allows us to build a more comprehensive (and pretty) API documentation of the entire library. We have more options to add comprehensive online search functionality in this solution as well.  
  
Furthermore, will hopefully be able to set it up so that we can maintain and publish separate documentations for each forthcoming release. That is, you should be able to read the docs for 1.0, 1.1 or the latest master development as you like (similarly to how Django does it, although probably not as fancy from the onset).   
  
This means that contributions to the documentation will be done as PRs through GitHub, just like when contributing any other code. While this does add a little more of a hurdle to contributions, hopefully the benefits will far outweigh those. Building the docs locally will not require a running Evennia server (unless you want the api docs) and we will try to set everything up for to make it easy to contribute.  
  
Many of the details around the docs are still up in the air. This is still very much work-in-progress, like everything else.  
  
Work with this has started in the static-file-docs branch of Evennia. But we have not closed the wiki either - the two will exist in parallel for now.  
  

### PyPi

  
As mentioned before,  we will finally start to distribute Evennia via PyPi (the Python Package Index) - that is, you will be able to run `pip install evennia`. Using GIT will no longer be a requirement to get started.  
  
Considering how quickly people in open-source throw up their three lines of code on PyPi these days, it may be surprising Evennia is not already on PyPi. I have however felt that reading and referencing the highly-commented code is a big part and requirement for getting the most out of the library.  
  
With the new documentation system, this would improve. And you can of course still use git and follow master branch like the good ol' days if you want!  
  

### Web Admin improvements

  
For the longest time, the Django-admin component has been somewhat on the back-burner. With the help of community contributors, this is improving so you will be able to do more work the Admin GUI related to creating and managing objects, tie puppets to Accounts etc.  

### API improvements 

  
Whereas the last few months have been mostly spent fixing lingering bugs, one thing planned for version 1.0 is a general cleanup of legacy strangeness in the API. For example, certain methods can return a list or a single object depending situation, which makes it hard to generalize. There are a lot of small quirks like that which we hope to address and make more consistent.  
  
There has also been a recent flurry of contributor PRs intended to help decouple Evennia's systems and make them easier to replace for those inclined to do so. Many of this is still being worked on, but it's likely you'll be able to replace many more "core" components for 1.0 with your own variations without doing any hacking in upstream code at all.  
 ... Needless to say, this is an advanced feature that most developers will never need. But Evennia was always intended to be heavily customizable and having the option is a good thing!  
  
Another feature that will come for 1.0 is a REST-API, added by one of our contributors. This uses Django-REST-Framework and makes it easier for external programs to authenticate and fetch data out of the Evennia database (great both for external apps, websites or custom what-have-you).  
At this time you can only fetch database objects via this interface, you cannot perform Command-calls or "play the game" this way (REST is a stateless concept and Evennia Commands tend to retain state).  
  

### Many other fixes and contributions

  
There's a truckload of stuff already available in master branch, but with the latest contributions of bigger code changes, we have started to use the Evennia develop branch again in earnest again. For a summary of the changes so far, check out the [Changelog](https://github.com/evennia/evennia/blob/develop/CHANGELOG.md).   
  
However, unless you want to contribute to Evennia itself (or really, really want to be on the bleeding edge), you are still recommended to use the master branch for now. A lot of work still to do, as said.