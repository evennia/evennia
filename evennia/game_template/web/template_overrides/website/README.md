You can replace the django templates (html files) for the website
here. It uses the default "prosimii" theme. If you want to maintain
multiple themes rather than just change the default one in-place, 
make new folders under `template_overrides/` and change
`settings.ACTIVE_THEME` to point to the folder name to use.

You can find the original files under `evennia/web/website/templates/website/`
