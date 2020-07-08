# Server Setup and Life

This documentation covers how to setup and maintain the server, from first install to opening your game to the public.

## Installation & running 

- [Installation & Setup quick-start](Setup-Quickstart) - one page to quickly get you going
- [Extended Install instructions](Extended-Installation) - if you have trouble or want to contribute to Evennia itself
- [Running through Docker](Running-Evennia-in-Docker) - alternative install method, useful for quick deployment on remote servers
- [Installing Evennia on Android](Installing-on-Android) - for those craving a mobile life
- [Controlling the server](Start-Stop-Reload) - an extended view on how to start/stop/update the server

## Installing custom game dirs

- [Installing Arxcode](../Contrib/Arxcode-installing-help) - a custom gamedir based on the popular Evennia game [Arx](https://play.arxgame.org/)

## Configuring

- [The settings file](Settings-File) - how and where to change the main settings of the server
- [Change database engine](Choosing-An-SQL-Server) - if you want to use something other than SQLite3
- [Evennia game index](Evennia-Game-Index) - register your upcoming game with the index to start the hype going


- [Chat on IRC](IRC) - how to link your game's channels to an external [IRC](https://en.wikipedia.org/wiki/Internet_Relay_Chat) channel
- [Chat on Grapevine](Grapevine) - how to link your game's channels the [Grapevine](https://grapevine.haus/) mud network/chat
- [Messages to RSS](RSS) - have your game notify people through RSS
- [Messages to Twitter](How-to-connect-Evennia-to-Twitter) - have Evennia send messages to [Twitter](https://twitter.com/) (requires some coding)

## Going public 

- [Notes about security](Security) - some things to think about to stay safe(r)
    - [Using HAProxy](HAProxy-Config) - putting a proxy in front of the game server for security
    - [Using Apache as a webserver](Apache-Config) - use Apache instead of Evennia's webserver (limited support)
- [Taking your server online](Online-Setup) - decide on where to host and configure your game for production
- [Client support grid](Client-Support-Grid) - clients known to work (or not) with Evennia
