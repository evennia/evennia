# Configuring NGINX for Evennia with SSL

[Nginx](https://nginx.org/en/) is a proxy server; you can put it between Evennia and the outside world to serve your game over encrypted connections. Another alternative is [HAProxy](./Config-HAProxy.md). 

> This is NOT a full set-up guide! It assumes you know how to get your own `Letsencrypt` certificates, that you already have nginx installed, and that you are familiar with Nginx configuration files. **If you don't already use nginx,** you are probably better off using the [guide for using HAProxy](./Config-HAProxy.md) instead.

## SSL on the website and websocket

Both the website and the websocket should be accessed through your normal HTTPS port, so they should be defined together.

For nginx, here is an example configuration, using Evennia's default ports:
```
server {
	server_name example.com;

	listen [::]:443 ssl;
	listen 443 ssl;
	ssl_certificate	 /path/to/your/cert/file;
	ssl_certificate_key /path/to/your/cert/key;

	location /ws {
		# The websocket connection
		proxy_pass http://localhost:4002;
		proxy_http_version 1.1;
		# allows the handshake to upgrade the connection
		proxy_set_header Upgrade $http_upgrade;
		proxy_set_header Connection "Upgrade";
		# forwards the connection IP
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header Host $host;
	}

	location / {
		# The main website
		proxy_pass http://localhost:4001;
		proxy_http_version 1.1;
		# forwards the connection IP
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header Host $http_host;
		proxy_set_header X-Forwarded-Proto $scheme;
	}
}
```

This proxies the websocket connection through the `/ws` location, and the root location to the website.

For Evennia, here is an example settings configuration that would go with the above nginx configuration, to go in your production server's `server/conf/secret_settings.py`

> The `secret_settings.py` file is not included in `git` commits and is to be used for secret stuff. Putting your production-only settings in this file allows you to continue using default access points for local development, making your life easier.

```python
SERVER_HOSTNAME = "example.com"
# Set the FULL URI for the websocket, including the scheme
WEBSOCKET_CLIENT_URL = "wss://example.com/ws"
# Turn off all external connections
LOCKDOWN_MODE = True
```
This makes sure that evennia uses the correct URI for websocket connections. Setting `LOCKDOWN_MODE` on will also prevents any external connections directly to Evennia's ports, limiting it to connections through the nginx proxies.

## Telnet SSL

> This will proxy ALL telnet access through nginx! If you want players to connect directly to Evennia's telnet ports instead of going through nginx, leave `LOCKDOWN_MODE` off and use a different SSL implementation, such as activating Evennia's internal telnet SSL port (see `settings.SSL_ENABLED` and `settings.SSL_PORTS` in  [default settings file](./Settings-Default.md)). 

If you've only used nginx for websites, telnet is slightly more complicated. You need to set up stream parameters in your primary configuration file - e.g. `/etc/nginx/nginx.conf` - which default installations typically will not include.

We chose to parallel the `http` structure for `stream`, adding conf files to `streams-available` and having them symlinked in `streams-enabled`, the same as other sites.

```
stream {
	include /etc/nginx/conf.streams.d/*.conf;
	include /etc/nginx/streams-enabled/*;
}
```
Then of course you need to create the required folders in the same location as your other nginx configurations:

    $ sudo mkdir conf.streams.d streams-available streams-enabled

An example configuration file for the telnet connection - using an arbitrary external port of `4040` - would then be:
```
server {
	listen [::]:4040 ssl;
	listen 4040 ssl;

	ssl_certificate  /path/to/your/cert/file;
	ssl_certificate_key  /path/to/your/cert/key;

	# connect to Evennia's internal NON-SSL telnet port
	proxy_pass localhost:4000;
	# forwards the connection IP - requires --with-stream-realip-module
	set_real_ip_from $realip_remote_addr:$realip_remote_port
}
```
Players can now connect with telnet+SSL to your server at `example.com:4040` - but *not* to the internal connection of `4000`.

> ***IMPORTANT: With this configuration, the default front page will be WRONG.*** You will need to change the `index.html` template and update the telnet section (NOT the telnet ssl section!) to display the correct information.


## Don't Forget!

`certbot` will automatically renew your certificates for you, but nginx won't see them without reloading. Make sure to set up a monthly cron job to reload your nginx service to avoid service interruptions due to expired certificates.
