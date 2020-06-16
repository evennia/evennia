# Administrative Docs

The following pages are aimed at game administrators -- the higher-ups that possess shell access and
are responsible for managing the game.

### Installation and Early Life

- [Choosing (and installing) an SQL Server](Choosing-An-SQL-Server)
- [Getting Started - Installing Evennia](Getting-Started)
- [Running Evennia in Docker Containers](Running-Evennia-in-Docker)
- [Starting, stopping, reloading and resetting Evennia](Start-Stop-Reload)
- [Keeping your game up to date](Updating-Your-Game)
 - [Resetting your database](Updating-Your-Game#resetting-your-database)
- [Making your game available online](Online-Setup)
  - [Hosting options](Online-Setup#hosting-options)
  - [Securing your server with SSL/Let's Encrypt](Online-Setup#ssl)
- [Listing your game](Evennia-Game-Index) at the online [Evennia game
index](http://games.evennia.com)

### Customizing the server

- [Changing the Settings](Server-Conf#Settings-file) 
    - [Available Master Settings](https://github.com/evennia/evennia/blob/master/evennia/settings_default.py)
- [Change Evennia's language](Internationalization) (internationalization)
- [Apache webserver configuration](Apache-Config) (optional)
- [Changing text encodings used by the server](Text-Encodings)
- [The Connection Screen](Connection-Screen)
- [Guest Logins](Guest-Logins)
- [How to connect Evennia to IRC channels](IRC)
- [How to connect Evennia to RSS feeds](RSS)
- [How to connect Evennia to Grapevine](Grapevine)
- [How to connect Evennia to Twitter](How-to-connect-Evennia-to-Twitter)

### Administrating the running game

- [Supported clients](Client-Support-Grid) (grid of known client issues)
- [Changing Permissions](Building-Permissions) of users
- [Banning](Banning) and deleting users
  - [Summary of abuse-handling tools](Banning#summary-of-abuse-handling-tools) in the default cmdset

### Working with Evennia

- [Setting up your work environment with version control](Version-Control)
- [First steps coding with Evennia](First-Steps-Coding)
- [Setting up a continuous integration build environment](Continuous-Integration)
