title: The blog moved!
copyrights: Images: [©Griatch](https://deviantart.com/griatch-art)

---

![to greener pastures image by Griatch](images/to_greener_pastures_by_griatch_art_smallview.jpg)

If you are reading this, you may notice that this blog has moved from [its old home](https://evennia.blogspot.com/) over on blogspot. I had no issues with blogspot except for the fact that writing the blog itself was done in a rather clunky editor with limited support for code.

Every other text in Evennia (docs, comments etc) is written in [markdown](https://en.wikipedia.org/wiki/Markdown) and I figured it would be nice to be able to use that also for my dev blog.

So I put together my own little blog platform.

## Making a little blog platform

I have rather small requirements - I don't publish a crazy amount of Evennia devblogs and I'm fine with making a git commit to do so.

I already use github pages for the [Evennia homepage](https://www.evennia.com) and [documentation](https://www.evennia.com/docs). These are simply html pages located in a `gh-pages` branch of the main `evennia` repo. So I decided I would just post my blog posts in a folder and then run a markdown parser to turn it into publisheable HTML pages.

### The tools
Markdown was originally made to be converted to HTML and there is a plethora of markdown parsers for Python. I also wanted an easy way to insert my text into HTML template; this is also a well-solved problem. So these are the tools I used:

- [mistletoe](https://github.com/miyuchina/mistletoe) is a pure-Python markdown->HTML parser. I had never used it before but it was easy to use and very fast. It also supports the `CommonMark` Markdown spec (same as github). I could also easily have it use [pygments](https://pygments.org/) to add code-highlighting to code snippets.
- [jinja2](https://jinja.palletsprojects.com/en/3.0.x/) is a way to embed special tags in HTML "templates" that can then be programmatically filled with content. It's very similar to the Django templating language.

### The posts

I then decided that each blog post should be one markdown file with a file name `YYYY-MM-DD-The-post-name.md`. So this current devblog has a file name of `2021-11-18-The-blog-moved.md`.

In its simplest form, the date and name of the blog is just parsed from the filename (also makes it easy to find in the file system). But I also decided that each post could have a little optional meta-header for customizing things:

```
title: The blog moved!
date: 2021-10-11
copyrights: Image: [©Griatch](https://deviantart.com/griatch-art)

---

Here the blog starts...
```

The `title` is mainly to be able to add characters like `!` or `?` that I don't want to add to the file name. I've not used the `date` yet, but I guess one could use it to publish a text at a different date than the filename (not sure why one would want that ...). The `copyrights` is to properly credit any resources (mostly images) used.

I wrote my own `build_devblog.py` program that simple reads all `.md` files from a directory. It figures out the date and title (from file name or meta-header) and runs `mistletoe` on it. I create a dataclass with all the post-relevant properties on it. So far so good. Now we need to inject this into an HTML structure.

### The html

Next I prepared a little `post.html` Jinja template:

```jinja
<h1 id={{ blogpost.anchor }}>
     {{ blogpost.title }}
     <a class="devblog-headerlink" href="{{ blogpost.permalink }}" title="Permalink to this blog post">¶</a>
    <div class="devblog-title-date">- {{ blogpost.date_pretty }}</div>
</h1>
{{ blogpost.html }}
<footer class="devblog-footer">
    <span class="devblog-copyrights">
        {{ blogpost.image_copyrights }}
    </span>
    <a class="devblog-to-toplink" href="{{ blogpost.permalink }}" title="Link to top of post">⇬(top)</a>
</footer>
```


Above, the `blogpost` is a dataclass made available to Jinja, from which it reads and inserts data into the HTML using the `{{ ... }}` templating fields.
I wanted each individual blog post to have a permalink, so that you could refer to it. I also decided that I would group all blog posts from a year into one HTML page, so `2021.html`, `2020.html` etc. Within each page, the blog post is just an anchor. So the link to this post is

    https://www.evennia.com/devblog/2021.html#2021-11-18-The-blog-moved

which seems quite clear.

For the entire year of devblogs, I stole the template used by the main `evennia.com` page, and also used the same CSS file (it's all in the same repo after all). Jinja allows you to do simple `for` loops within the template so it's easy to add all posts into a page.


### The CSS

The final bit was to clean up the CSS and make a little 'calendar' in the sidebar to make it easy to navigate to older devblogs. In the wide-page view you can hover over the blog dates to see their names for easy lookup.

### Converting the old blog

Google (which owns blogspot (formar Blogger) has an export feature but the result of this is a very dense XML file. It's mainly intended to be imported by Wordpress or some other existing blog platform. In the end I gave up on trying to parse it.

Instead I went the dumb route and just copy&pasted each of my old blogs from the old blog into Obsidian, which I use for markdown editing. Luckily this worked very well - all layout was retained and converted automatically to markdown syntax, including links to images etc. I only needed to add some nicer markup for code strings (since that was not a thing on blogspot).

I don't know if I have Obsidian to thank for this or if blogspot uses some standardized format, but manually converti of all my devblogs since 2012 thus ended up being a lot less painful than I thought (for once).


### Things lost in move

There are a few things that were possible on blogspot that my simple little custom platform cannot do.

- Online editing: I'm not posting things on the fly so I'm fine with making a commit. Writing in a proper text editor is more confortable anyway. And the posts are under version control too!
- Comments: Few people every commented directly in the old blog though - and lately it has mostly been spam. To comment, people'll need to use our forums on github or the support channel.
- Notifications: I haven't added an RSS feed for this page and there is thus no automatic reporting of new posts in chat etc. I think the amount of posts I do is low enough that I can advertise them manually. I'll probably just make a dedicated announcement thread in Github discussions.


## Onward

So, with this new blog platform in place (this post is the first one I write using the new system), I won't update the old one anymore. The old one's not going anywhere though, and I will point here from it.

The new Evennia site ecosystem is getting a little more compact. These are services hosted on github/github pages:

- Homepage - [https://www.evennia.com](https://www.evennia.com)
- Docs - [https://www.evennia.com/docs](https://www.evennia.com/docs)
- Devblog - [https://www.evennia.com/devblog](https://www.evennia.com/devblog)
- Forums - [https://github.com/evennia/evennia/discussions](https://github.com/evennia/evennia/discussions)
- Code - [https://github.com/evennia/evennia](https://github.com/evennia/evennia

At this point, the only things running elsewhere (and which will continue doing so) are:

- [https://games.evennia.com](https://games.evennia.com) - runs on Google App Engine
- [https://demo.evennia.com](https://demo.evennia.com) - Digital Ocean droplet
- [https://discord.gg/AJJpcRUhtF](https://discord.gg/AJJpcRUhtF) - Discord server (duh)

There is also an old version of the docs on `ReadTheDocs`. This is out of date and should be removed ...

But overall, the Evennia ecosystem is getting more and more cleaned up as we (slowly) approach the release of Evennia 1.0 ...