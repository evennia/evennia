# Docs refactoring

This is a whitepage for free discussion about the wiki docs and refactorings needed.

Note that this is not a forum. To keep things clean, each opinion text should ideally present a
clear argument or lay out a suggestion. Asking for clarification and any side-discussions should be
held in chat or forum.

### Griatch (Aug 13, 2019)

This is how to make a discussion entry for the whitepage. Use any markdown formatting you need. Also
remember to copy your work to the clipboard before saving the page since if someone else edited the
page since you started, you'll have to reload and write again.

#### (Sept 23, 2019)
    
[This (now closed) issue by DamnedScholar](https://github.com/evennia/evennia/issues/1431) gives the
following suggestion:
> I think it would be useful for the pages that explain how to use various features of Evennia to
have explicit and easily visible links to the respective API entry or entries. Some pages do, but
not all. I imagine this as a single entry at the top of the page [...].

[This (now closed) issue by taladan](https://github.com/evennia/evennia/issues/1578) gives the
following suggestion:
> It would help me (and probably a couple of others) if there is a way to show the file path where a
particular thing exists. Maybe up under the 'last edited' line we could have a line like:
evennia/locks/lockhandler.py

This would help in development to quickly refer to where a resource is located.
   

### Kovitikus (Sept. 11, 2019)

[Batch Code](./Batch-Code-Processor.md) should have a link in the developer area. It is currently only
listed in the tutorials section as an afterthought to a tutorial title.

***

In regards to the general structure of each wiki page: I'd like to see a table of contents at the
top of each one, so that it can be quickly navigated and is immediately apparent what sections are
covered on the page. Similar to the current [Getting Started](./Getting-Started.md) page.

***

The structuring of the page should also include a quick reference cheatsheet for certain aspects.
Such as [Tags](./Tags.md) including a quick reference section at the top that lists an example of every
available method you can use in a clear and consistent format, along with a comment. Readers
shouldn't have to decipher the article to gather such basic information and it should instead be
available at first glance.

Example of a quick reference:

**Tags**
```
# Add a tag.
obj.tags.add("label")

# Remove a tag.
obj.tags.remove("label")

# Remove all tags.
obj.tags.clear()

# Search for a tag. Evennia must be imported first.
store_result = evennia.search_tag("label")

# Return a list of all tags.
obj.tags.all()
```

**Aliases**
```
# Add an alias.
obj.aliases.add("label")

ETC...
```

***

In regards to comment structure, I often find that smushing together lines with comments to be too
obscure. White space should be used to clearly delineate what information the comment is for. I
understand that the current format is that a comment references whatever is below it, but newbies
may not know that until they realize it.

Example of poor formatting:
```
#comment
command/code
#comment
command/code
```

Example of good formatting:
```
# Comment.
command/code

# Comment.
command/code
```

### Sage (3/28/20)

If I want to find information on the correct syntax for is_typeclass(), here's what I do:
* Pop over to the wiki. Okay, this is a developer functionality. Let's try that.
* Ctrl+F on Developer page. No results.
* Ctrl+F on API page. No results. Ctrl+F on Flat API page. No results
* Ctrl+F on utils page. No results.
* Ctrl+F on utils.utils page. No results.
* Ctrl+F in my IDE. Results.
* Fortunately, there's only one result for def is_typeclass. If this was at_look, there would be
several results, and I'd have to go through each of those individually, and most of them would just
call return_appearance

An important part of a refactor, in my opinion, is separating out the "Tutorials" from the
"Reference" documentation.
