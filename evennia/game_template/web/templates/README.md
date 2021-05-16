# HTML templates

Templates are HTML files that (usually) have special `{{ ... }}` template
markers in them to allow Evennia/Django to insert dynamic content in a web
page. An example is listing how many users are currently online in the game.

Templates are referenced by _views_ - Python functions or callable classes that
prepare the data needed by the template and 'renders' them into a finished 
HTML page to return to the user.

You can replace Evennia's default templates by overriding them in this folder.
The originals are in `evennia/web/templates/` - just copy the template into the
corresponding location here (so the website's `index.html` should be copied to
`website/index.html` where it can be modified). Reload the server to see your changes.
