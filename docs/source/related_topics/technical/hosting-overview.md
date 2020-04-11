```python
class Documentation:
    RATING = "Excellent"
```

# Hosting Documentation

This documentation covers installation of Evennia in a production environment on either Linux or Windows.
The vast majority of systems in operation today should support Evennia.

## Installation
Review the [installation](../../evennia_core/setup/installation) documentation.

## Connecting to Evennia
Review the [connecting to Evennia](../../evennia_core/setup/connecting) documentation.

## Advanced Server Administration
### Upgrading Evennia
Very commonly we make changes to the Evennia code to improve things. While we try very hard not to introduce changes that will break your game on an upgrade, this is still a beta.  

When you're wanting to apply updates, simply `cd` to your cloned `evennia` root directory and type:

     git pull
     evennia reboot

Note that this will disconnect all connected players.

For more information, particularly when moving between major versions of evennia, read [Updating Your Game](Updating-Your-Game)

|_Protip_|Stay in the loop|
|---|---|
|![JörMUDgandr][logo] | _JörMUDgandr says, "There are many ways to get told when to update: You can subscribe to the RSS feed or manually check up on the feeds from http://www.evennia.com. You can also simply fetch the latest regularly."_ |

### Logs
The server logs are in `mygame/server/logs/`. To easily view server logs in the terminal,
you can run `evennia -l`, or (in the future) start the server with `evennia start -l`.

### Game Admin Commands
Evennia supports the following commands. You can use these while inside your `evenv` virtual environment, so
be sure to `source evenv/bin/activate` (Unix) or `source evenv\Scripts\activate` (Windows) before continuing.

- `evennia restart` - The graceful way to restart a server to apply changes. Does not disconnect users.
- `evennia reboot` - Reboots both server and portal, disconnecting all users. Necessary after development changes very "deep" pieces of evennia, like settings.py
- `evennia kill` - The most destructive server restart. Kills processes defined in `server/server.pid` and `server/portal.pid`. Tries to be graceful, but no guarantees.
- `evennia start` - Starts the server
- `evennia stop` - Stops the server gracefully

For more information about these commands, as well as several others that are available, read the detailed guide over at [Stop/Start/Reload](Start-Stop-Reload).

### Database Management

Database handling is managed by [Django](https://docs.djangoproject.com/en/3.0/ref/databases/). The default database is sqlite3.
To use a different database, edit `server/conf/secret_settings.py` and update the `DATABASES=` key.

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydatabase',
        'USER': 'mydatabaseuser',
        'PASSWORD': 'mypassword',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}
```

The `evennia migrate` command builds the necessary tables. This command should only be run after changes which require the database to be reconstructed from scratch.

For more information, read [Choosing (and installing) an SQL Server](../../related_topics/technical/databases)


### Protocols/Ports

Your firewall will hopefully block the necessary ports for remote connection on initial installation. The default external ports are described below:

- **4000**: Telnet
- **4001**: HTTP
- **4002**: Websockets

You can change these ports by modifying `settings.py` - defaults are listed below:

**Telnet**
```python
# Activate telnet service
TELNET_ENABLED = True

# A list of ports the Evennia telnet server listens on Can be one or many.
TELNET_PORTS = [4000]

# Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
TELNET_INTERFACES = ["0.0.0.0"]

# OOB (out-of-band) telnet communication allows Evennia to communicate
# special commands and data with enabled Telnet clients. This is used
# to create custom client interfaces over a telnet connection. To make
# full use of OOB, you need to prepare functions to handle the data
# server-side (see INPUT_FUNC_MODULES). TELNET_ENABLED is required for this
# to work.
TELNET_OOB_ENABLED = False
```
**SSL/SSH**
```python
# Activate Telnet+SSL protocol (SecureSocketLibrary) for supporting clients
SSL_ENABLED = False

# Ports to use for Telnet+SSL
SSL_PORTS = [4003]

# Telnet+SSL Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
SSL_INTERFACES = ["0.0.0.0"]

# Activate SSH protocol communication (SecureShell)
SSH_ENABLED = False

# Ports to use for SSH
SSH_PORTS = [4004]

# Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
SSH_INTERFACES = ["0.0.0.0"]
```
Read more about [securing your server with SSL/Let's Encrypt](../../related_topics/technical/online-setup)

**HTTP**
```python
# Start the evennia django+twisted webserver so you can
# browse the evennia website and the admin interface
# (Obs - further web configuration can be found below
# in the section  'Config for Django web features')
WEBSERVER_ENABLED = True

# This is a security setting protecting against host poisoning
# attacks.  It defaults to allowing all. In production, make
# sure to change this to your actual host addresses/IPs.
ALLOWED_HOSTS = ["*"]

# The webserver sits behind a Portal proxy. This is a list
# of tuples (proxyport,serverport) used. The proxyports are what
# the Portal proxy presents to the world. The serverports are
# the internal ports the proxy uses to forward data to the Server-side
# webserver (these should not be publicly open)
WEBSERVER_PORTS = [(4001, 4005)]

# Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
WEBSERVER_INTERFACES = ["0.0.0.0"]

# IP addresses that may talk to the server in a reverse proxy configuration,
# like NginX.
UPSTREAM_IPS = ["127.0.0.1"]

# The webserver uses threadpool for handling requests. This will scale
# with server load. Set the minimum and maximum number of threads it
# may use as (min, max) (must be > 0)
WEBSERVER_THREADPOOL_LIMITS = (1, 20)

# Start the evennia webclient. This requires the webserver to be running and
# offers the fallback ajax-based webclient backbone for browsers not supporting
# the websocket one.
WEBCLIENT_ENABLED = True
```
- [Apache Configuration](../../related_topics/technical/apache-config)

**Websockets**
```python
# Activate Websocket support for modern browsers. If this is on, the
# default webclient will use this and only use the ajax version if the browser
# is too old to support websockets. Requires WEBCLIENT_ENABLED.
WEBSOCKET_CLIENT_ENABLED = True

# Server-side websocket port to open for the webclient. Note that this value will
# be dynamically encoded in the webclient html page to allow the webclient to call
# home. If the external encoded value needs to be different than this, due to
# working through a proxy or docker port-remapping, the environment variable
# WEBCLIENT_CLIENT_PROXY_PORT can be used to override this port only for the
# front-facing client's sake.
WEBSOCKET_CLIENT_PORT = 4002

# Interface addresses to listen to. If 0.0.0.0, listen to all. Use :: for IPv6.
WEBSOCKET_CLIENT_INTERFACE = "0.0.0.0"

# Actual URL for webclient component to reach the websocket. You only need
# to set this if you know you need it, like using some sort of proxy setup.
# If given it must be on the form "ws[s]://hostname[:port]". If left at None,
# the client will itself figure out this url based on the server's hostname.
# e.g. ws://external.example.com or wss://external.example.com:443
WEBSOCKET_CLIENT_URL = None

```
**Lockdown**
```python
# Lockdown mode will cut off the game from any external connections
# and only allow connections from localhost. Requires a cold reboot.
LOCKDOWN_MODE = False
```
**AMP (Internal)**
```
# The Server opens an AMP port so that the portal can
# communicate with it. This is an internal functionality of Evennia, usually
# operating between two processes on the same machine. You usually don't need to
# change this unless you cannot use the default AMP port/host for
# whatever reason.

AMP_HOST = "localhost"
AMP_PORT = 4006
AMP_INTERFACE = "127.0.0.1"
```

[logo]: https://raw.githubusercontent.com/evennia/evennia/master/evennia/web/website/static/website/images/evennia_logo.png