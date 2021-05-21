# Webserver

When Evennia starts it also spins up its own Twisted-based web server. The webserver is responsible for serving the html pages of the game's website. It can also serve static resources like images and music.

The webclient runs as part of the [Server](Portal-And-Server) process of Evennia. This means that it can directly access cached objects modified in-game, and there is no risk of working with objects that are temporarily out-of-sync in the database.

The webserver runs on Twisted and is meant to be used in a production environment. It leverages the Django web framework and provides:

- A [Game Website](Website) - this is what you see when you go to `localhost:4001`. The look of the website is meant to be customized to your game. Users logged into the website will be auto-logged into the game if they do so with the webclient since they share the same login credentials (there is no way to safely do auto-login with telnet clients).
- The [Web Admin](Web-Admin) is based on the Django web admin and allows you to edit the game database in a graphical interface.
- The [Webclient](Webclient) page is served by the webserver, but the actual game communication (sending/receiving data) is done by the javascript client on the page opening a websocket connection directly to Evennia's Portal.