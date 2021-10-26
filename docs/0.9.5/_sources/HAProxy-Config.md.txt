# HAProxy Config (Optional)

## Making Evennia, HTTPS and Secure Websockets play nicely together

This we can do by installing a _proxy_ between Evennia and the outgoing ports of your server.
Essentially,
Evennia will think it's only running locally (on localhost, IP 127.0.0.1) - the proxy will
transparently
map that to the "real" outgoing ports and handle HTTPS/WSS for us.

```
Evennia <-> (inside-visible IP/ports) <-> Proxy <-> (outside-visible IP/ports) <-> Internet
```


Here we will use [HAProxy](https://www.haproxy.org/), an open-source proxy that is easy to set up
and use. We will
also be using [LetsEncrypt](https://letsencrypt.org/getting-started/), especially the excellent
helper-program [Certbot](https://certbot.eff.org/instructions) which pretty much automates the whole
certificate setup process for us.

Before starting you also need the following:

- (optional) The host name of your game (like `myawesomegame.com`). This is something you must
previously have purchased from a _domain registrar_ and set up with DNS to point to the IP of your
server.
- If you don't have a domain name or haven't set it up yet, you must at least know the IP of your
server. Find this with `ifconfig` or similar from inside the server. If you use a hosting service
like DigitalOcean you can also find the droplet's IP address in the control panel.
- You must open port 80 in your firewall. This is used by Certbot below to auto-renew certificates.
So you can't really run another webserver alongside this setup without tweaking.
- You must open port 443 (HTTPS) in your firewall.
- You must open port 4002 (the default Websocket port) in your firewall.


## Getting certificates

Certificates guarantee that you are you. Easiest is to get this with
[Letsencrypt](https://letsencrypt.org/getting-started/) and the
[Certbot](https://certbot.eff.org/instructions) program. Certbot has a lot of install instructions
for various operating systems. Here's for Debian/Ubuntu:

```
sudo apt install certbot
```

Make sure to stop Evennia and that no port-80 using service is running, then

```
sudo certbot certonly --standalone
```

You will get some questions you need to answer, such as an email to send certificate errors to and
the host name (or IP, supposedly) to use with this certificate. After this, the certificates will
end up in `/etc/letsencrypt/live/<your-host-or-ip>/*pem` (example from Ubuntu). The critical files
for our purposes are `fullchain.pem` and `privkey.pem`.

Certbot sets up a cron-job/systemd job to regularly renew the certificate. To check this works, try

```
sudo certbot renew --dry-run
```

The certificate is only valid for 3 months at a time, so make sure this test works (it requires port
80 to be open). Look up Certbot's page for more help.

We are not quite done. HAProxy expects these two files to be _one_ file.

```
sudo cp /etc/letsencrypt/live/<your-host-or-ip>/privkey.pem /etc/letsencrypt/live/<your-host-or-
ip>/<yourhostname>.pem
sudo bash -c "cat /etc/letsencrypt/live/<your-host-or-ip>/fullchain.pem >>
/etc/letsencrypt/live/<your-host-or-ip>/<yourhostname>.pem"
```

This will create a new `.pem` file by concatenating the two files together. The `yourhostname.pem`
file (or whatever you named it) is what we will use when the the HAProxy config file (below) asks
for "your-certificate.pem".

## Installing and configuring HAProxy

Installing HaProxy is usually as simple as:
```
# Debian derivatives (Ubuntu, Mint etc)
sudo apt install haproxy

# Redhat derivatives (dnf instead of yum for very recent Fedora distros)
sudo yum install haproxy

```

Configuration of HAProxy is done in a single file. Put this wherever you like, for example in
your game dir; name it something like haproxy.conf.

Here is an example tested on Centos7 and Ubuntu. Make sure to change the file to put in your own
values.

```
# base stuff to set up haproxy
global
    log /dev/log local0
    chroot /var/lib/haproxy
    maxconn  4000
    user  haproxy
    tune.ssl.default-dh-param 2048
    ## uncomment this when everything works
    # daemon
defaults
    mode http
    option forwardfor

# Evennia Specifics
listen evennia-https-website
    bind <ip-address-or-hostname>:<public-SSL-port--probably-443> ssl no-sslv3 no-tlsv10 crt
/etc/letsencrypt/live/<your-host-or-ip>/<yourhostname>.pem
    server localhost 127.0.0.1:<evennia-web-port-probably-4001>
    timeout client 10m
    timeout server 10m
    timeout connect 5m

listen evennia-secure-websocket
    bind <ip-address-or-hostname>:<wss-port--probably-4002> ssl no-sslv3 no-tlsv10 crt
/etc/letsencrypt/live/<your-host-or-ip>/<yourhostname>.pem
    server localhost 127.0.0.1:<WEBSOCKET_CLIENT_PORT-probably-4002>
    timeout client 10m
    timeout server 10m
    timeout connect 5m
```

## Putting it all together

Get back to the Evennia game dir and edit mygame/server/conf/settings.py. Add:

```
WEBSERVER_INTERFACES = ['127.0.0.1']
WEBSOCKET_CLIENT_INTERFACE = '127.0.0.1'
```
and
```
WEBSOCKET_CLIENT_URL="wss://fullhost.domain.name:4002/"
```

Make sure to reboot (stop + start) evennia completely:

```
evennia reboot
```


Finally you start the proxy:

```
sudo haproxy -f /path/to/the/above/config_file.cfg
```

Make sure you can connect to your game from your browser and that you end up with an `https://` page
and can use the websocket webclient.

Once everything works you may want to start the proxy automatically and in the background. Stop the
proxy with `Ctrl-C` and uncomment the line `# daemon` in the config file, then start the proxy again
- it will now start in the bacground.

You may also want to have the proxy start automatically; this you can do with `cron`, the inbuilt
Linux mechanism for running things at specific times.

```
sudo crontab -e
```

Choose your editor and add a new line at the end of the crontab file that opens:

```
@reboot haproxy -f /path/to/the/above/config_file.cfg
```

Save the file and haproxy should start up automatically when you reboot the server.