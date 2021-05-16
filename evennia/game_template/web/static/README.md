## Static files

This is the place to put static resources you want to serve from the 
Evennia server. This is usually CSS and Javascript files but you _could_ also
serve other media like images, videos and music files from here.

> If you serve a lot of large files (especially videos) you will see a lot
> better performance doing so from a separate dedicated media host.

You can also override default Evennia files from here. The original files are
found in `evennia/web/static/`. Copy the original file into the same
corresponding location/sublocation in this folder (such as website CSS files
into `mygame/static/website/css/`) and modify it, then reload the server.

Note that all static resources will be collected from all over Evennia into
`mygame/server/.static` for serving by the webserver. That folder should not be
modified manually.
