If you want to override one of the static files (such as a CSS or JS file) used by Evennia or a Django app installed in your Evennia project,
copy it into this directory's corresponding subdirectory, and it will be placed in the static folder when you run:

    python manage.py collectstatic

...or when you reload the server via the command line.

Do note you may have to reproduce any preceeding directory structures for the file to end up in the right place.

Also note that you may need to clear out existing static files for your new ones to be gathered in some cases. Deleting files in static/ 
will force them to be recollected.

To see what files can be overridden, find where your evennia package is installed, and look in `evennia/web/static/`
