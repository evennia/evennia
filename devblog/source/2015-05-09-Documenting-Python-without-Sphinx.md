copyrights: (Image from [Wikimedia commons](http://en.wikipedia.org/wiki/File:La_Granja_de_San_Ildefonso_Sfinx01.jpg))

---

[![](https://lh4.googleusercontent.com/proxy/KbIwdEDoKI3YPVgVArY87c8tHYHbRamzP5RsqyRKu62rVXabv9fFLBgcMorVujBaKdsfxtKnFpUUNS1z3OkGBo-en1f9pwaNyYeTu08PxNSR3EB_Zjvs9LtQfcSzXx_h7dU4RdnC81jTtAkfoGEewKp4KOP3dnml_Z6yAMdPFWHjU_r8T5_jjC7Oi0pKp3w1PV9_ep2u9zCF1dLEgvoHDIs=s0-d)](http://upload.wikimedia.org/wikipedia/commons/thumb/f/fd/La_Granja_de_San_Ildefonso_Sfinx01.jpg/800px-La_Granja_de_San_Ildefonso_Sfinx01.jpg)

Last week Evennia merged its development branch [with all the features mentioned in the last post](http://evennia.blogspot.se/2015/01/building-django-proxies-and-mud.html). Post-merger we have since gone through and fixed remaining bugs and shortened the list at a good clip.  
  
One thing I have been considering is how to make Evennia's API auto-documenting - we are after all a MUD creation library and whereas our code has always been well-documented the docs were always only accessible from the source files themselves.  
  
Now, when you hear "Python" and "documentation" in the same sentence, the first thought usually involves Sphinx or [Sphinx autodoc](http://sphinx-doc.org/ext/autodoc.html) in some form. Sphinx produces [very nice looking documentation](https://docs.djangoproject.com/en/1.7/) indeed. My problem is however as follows:  

-   I don't want our API documentation to be written in a different format from the rest of our documentation, which is in Github's wiki using Markdown.  Our users should be able to help document Evennia without remembering which formatting language is to be used.
-   I don't like reStructuredText syntax. This is a personal thing. I get that it is powerful but it is also really, really ugly to read in its raw form in the source code. I feel the sources must be easy to read on their own.
-   Sphinx plugins like [napoleon](http://sphinx-doc.org/latest/ext/napoleon.html) understands this ugliness and allows you to document your functions and classes in a saner form, such as the "Google style". One still needs reST for in-place formatting though.
-   Organizing sphinx document trees is fiddly and having had a few runs with sphinx autodoc it's just a mess trying to get it to section the Evennia sources in a way that makes sense. It could probably be done if I worked a lot more with it, but it's a generic page generator and I feel that I will eventually have to get down to make those toctrees myself before I'm happy.
-   I want to host the API docs as normal Wiki files on Github (this might be possible with reST too I suppose).

  
Long story short, rather than messing with getting Sphinx to do what I want, I ended up writing my own api-to-github-Markdown parser for the Evennia sources: api2md. Using Python's inspect module and aiming for a subset of the [Google formatted docstrings](http://sphinx-doc.org/latest/ext/example_google.html), this was maybe a day's work in total - the rest was/is fine-tuning for prettiness.  
   
Now whenever the source is updated, I follow the following procedure to fully update the API docs:  
  

1.  I pull the latest version of Evennia's wiki git repository from github alongside the latest version of the main Evennia repository.
2.  I run api2md on the changed Evennia sources. This crawls the main repo for top-level package imports (which is a small list currently hard-coded in the crawler - this is to know which modules should create "submodule" pages rather than try to list class contents etc). Under each package I specify it then recursively gets all modules. For each module in that package, it creates a new Markdown formatted wiki page which it drops in a folder in the wiki repository. The files are named after the model's path in the library, meaning you get files like evennia.objects.models.md and can easily cross-link to subsections (aka classes and functions) on a page using page anchors.
3.  I add eventual new files and commit the changes, then push the result to the Github wiki online. Done!

(I could probably automate this with a git hook. Maybe as a future project.)  
  
The api2md program currently has some Evennia-custom elements in it (notably in which packages it imports) but it's otherwise a very generic parser of Python code into Markdown. It could maybe be broken out into its own package at some point if there's interest.     
  
The interesting thing is that since I already have code for [converting our wiki to reST](http://evennia.blogspot.se/2014/02/moving-from-google-code-to-github.html) and ReadTheDocs, I should be able to get the best of both worlds and convert our API wiki pages the same way later. The result will probably not be quite as custom-stunning as a Sphinx generated autodoc (markdown is a lot simpler in what formatting options it can offer) but that is a lesser concern.  
So far very few of Evennia's docstrings are actually updated for the Google style syntax (or any type of formatting, really) so the result is often not too useful. We hope that many people will help us with the doc strings in the future - it's a great and easy way to get to know Evennia while helping out.  
  
But where the sources _are_ updated, [the auto-generated wiki page looks pretty neat](https://github.com/evennia/evennia/wiki/evennia.utils.evtable).  
