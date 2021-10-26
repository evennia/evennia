# Administrative Docs

The following pages are aimed at game administrators -- the higher-ups that possess shell access and
are responsible for managing the game.

### Installation and Early Life

- [Choosing (and installing) an SQL Server](./Choosing-An-SQL-Server.md)
- [Getting Started - Installing Evennia](./Getting-Started.md)
- [Running Evennia in Docker Containers](./Running-Evennia-in-Docker.md)
- [Starting, stopping, reloading and resetting Evennia](./Start-Stop-Reload.md)
- [Keeping your game up to date](./Updating-Your-Game.md)
 - [Resetting your database](./Updating-Your-Game.md#resetting-your-database)
- [Making your game available online](./Online-Setup.md)
  - [Hosting options](./Online-Setup.md#hosting-options)
  - [Securing your server with SSL/Let's Encrypt](./Online-Setup.md#ssl)
- [Listing your game](./Evennia-Game-Index.md) at the online [Evennia game
index](http://games.evennia.com)

### Customizing the server

- [Changing the Settings](./Server-Conf.md#settings-file)
    - [Available Master
Settings](https://github.com/evennia/evennia/blob/master/evennia/settings_default.py)
- [Change Evennia's language](./Internationalization.md) (internationalization)
- [Apache webserver configuration](./Apache-Config.md) (optional)
- [Changing text encodings used by the server](./Text-Encodings.md)
- [The Connection Screen](./Connection-Screen.md)
- [Guest Logins](./Guest-Logins.md)
- [How to connect Evennia to IRC channels](./IRC.md)
- [How to connect Evennia to RSS feeds](./RSS.md)
- [How to connect Evennia to Grapevine](./Grapevine.md)
- [How to connect Evennia to Twitter](./How-to-connect-Evennia-to-Twitter.md)

### Administrating the running game

- [Supported clients](./Client-Support-Grid.md) (grid of known client issues)
- [Changing Permissions](./Building-Permissions.md) of users
- [Banning](./Banning.md) and deleting users
  - [Summary of abuse-handling tools](./Banning.md#summary-of-abuse-handling-tools) in the default cmdset

### Working with Evennia

- [Setting up your work environment with version control](./Version-Control.md)
- [First steps coding with Evennia](./First-Steps-Coding.md)
- [Setting up a continuous integration build environment](./Continuous-Integration.md)


```{toctree}
    :hidden:

    Choosing-An-SQL-Server
    Getting-Started
    Running-Evennia-in-Docker
    Start-Stop-Reload
    Updating-Your-Game
    Online-Setup
    Evennia-Game-Index
    Server-Conf
    Internationalization
    Apache-Config
    Text-Encodings
    Connection-Screen
    Guest-Logins
    IRC
    RSS
    Grapevine
    How-to-connect-Evennia-to-Twitter
    Client-Support-Grid
    Building-Permissions
    Banning
    Version-Control
    First-Steps-Coding
    Continuous-Integration 

```