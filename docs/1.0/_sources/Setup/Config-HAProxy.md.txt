# Configuring HAProxy

A modern public-facing website should these days be served via encrypted
connections. So `https:` rather than `http:` for the website and
`wss:` rather than vs `ws:` for websocket connections used by webclient.

The reason is security - not only does it make sure a user ends up at the right
site (rather than a spoof that hijacked the original's address), it stops an
evil middleman from snooping on data (like passwords) being sent across the
wire.

Evennia itself does not implement https/wss connections. This is something best
handled by dedicated tools able to keep up-to-date with the latest security
practices.

So what we'll do is install _proxy_ between Evennia and the outgoing ports of
your server.  Essentially, Evennia will think it's only running locally (on
localhost, IP 127.0.0.1) while the proxy will transparently map that to the
"real" outgoing ports and handle HTTPS/WSS for us.

             Evennia
                |
    (inside-only local IP/ports serving HTTP/WS)
                |
              Proxy
                |
    (outside-visible public IP/ports serving HTTPS/WSS)
                |
             Firewall
                |
             Internet

These instructions assume you run a server with Unix/Linux (very common if you
use remote hosting) and that you have root access to that server.

The pieces we'll need:

- [HAProxy](https://www.haproxy.org/) - an open-source proxy program that is
  easy to set up and use.
- [LetsEncrypt](https://letsencrypt.org/getting-started/) for providing the User
  Certificate needed to establish an encrypted connection. In particular we'll
  use the excellent [Certbot](https://certbot.eff.org/instructions) program,
  which automates the whole certificate setup process with LetsEncrypt.
- `cron` - this comes with all Linux/Unix systems and allows to automate tasks
  in the OS.

Before starting you also need the following information and setup:

- (optional) The host name of your game. This is
  something you must previously have purchased from a _domain registrar_ and set
  up with DNS to point to the IP of your server. For the benefit of this
  manual, we'll assume your host name is `my.awesomegame.com`.
- If you don't have a domain name or haven't set it up yet, you must at least
  know the IP address of your server. Find this with `ifconfig` or similar from
  inside the server. If you use a hosting service like DigitalOcean you can also
  find the droplet's IP address in the control panel. Use this as the host name
  everywhere.
- You must open port 80 in your firewall. This is used by Certbot below to
  auto-renew certificates.  So you can't really run another webserver alongside
  this setup without tweaking.
- You must open port 443 (HTTPS) in your firewall. This will be the external
  webserver port.
- Make sure port 4001 (internal webserver port) is _not_ open in your firewall
  (it usually will be closed by default unless you explicitly opened it
  previously).
- Open port 4002 in firewall (we'll use the same number for both internal-
  and external ports, the proxy will only show the safe one serving wss).

## Getting certificates

Certificates guarantee that you are you. Easiest is to get this with
[Letsencrypt](https://letsencrypt.org/getting-started/) and the
[Certbot](https://certbot.eff.org/instructions) program. Certbot has a lot of
install instructions for various operating systems. Here's for Debian/Ubuntu:

    sudo apt install certbot

Make sure to stop Evennia and that no port-80 using service is running, then

    sudo certbot certonly --standalone

You will get some questions you need to answer, such as an email to send
certificate errors to and the host name (or IP, supposedly) to use with this
certificate. After this, the certificates will end up in
`/etc/letsencrypt/live/<yourhostname>/*pem` (example from Ubuntu). The
critical files for our purposes are `fullchain.pem` and `privkey.pem`.

Certbot sets up a cron-job/systemd job to regularly renew the certificate. To
check this works, try

```
sudo certbot renew --dry-run

```

The certificate is only valid for 3 months at a time, so make sure this test
works (it requires port 80 to be open). Look up Certbot's page for more help.

We are not quite done. HAProxy expects these two files to be _one_ file. More
specifically we are going to
1. copy `privkey.pem` and copy it to a new file named `<yourhostname>.pem` (like
   `my.awesomegame.com.pem`)
2. Append the contents of `fullchain.pem` to the end of this new file. No empty
   lines are needed.

We could do this by copy&pasting in a text editor, but here's how to do it with
shell commands (replace the example paths with your own):

    cd /etc/letsencrypt/live/my.awesomegame.com/
    sudo cp privkey.pem my.awesomegame.com.pem
    sudo cat fullchain.pem >> my.awesomegame.com.pem

The new `my.awesomegame.com.pem` file (or whatever you named it) is what we will
point to in the HAProxy config below.

There is a problem here though - Certbot will (re)generate `fullchain.pem` for
us automatically a few days before before the 3-month certificate runs out.
But HAProxy will not see this because it is looking at the combined file that
will still have the old `fullchain.pem` appended to it.

We'll set up an automated task to rebuild the `.pem` file regularly by
using the `cron` program of Unix/Linux.

    crontab -e

An editor will open to the  crontab file. Add the following at the bottom (all
on one line, and change the paths to your own!):

    0 5 * * * cd /etc/letsencrypt/live/my.awesomegame.com/ &&
        cp privkey.pem my.awesomegame.com.pem &&
        cat fullchain.pem >> my.awesomegame.com.pem

Save and close the editor. Every night at 05:00 (5 AM), the
`my.awesomegame.com.pem` will now be rebuilt for you. Since Certbot updates
the `fullchain.pem` file a few days before the certificate runs out, this should
be enough time to make sure HaProxy never sees an outdated certificate.

## Installing and configuring HAProxy

Installing HaProxy is usually as simple as:

    # Debian derivatives (Ubuntu, Mint etc)
    sudo apt install haproxy

    # Redhat derivatives (dnf instead of yum for very recent Fedora distros)
    sudo yum install haproxy

Configuration of HAProxy is done in a single file. This can be located wherever
you like, for now put in your game dir and name it `haproxy.cfg`.

Here is an example tested on Centos7 and Ubuntu. Make sure to change the file to
put in your own values.

We use the `my.awesomegame.com` example here and here are the ports

- `443` is the standard SSL port
- `4001` is the standard Evennia webserver port (firewall closed!)
- `4002` is the default Evennia websocket port (we use the same number for
  the outgoing wss port, so this should be open in firewall).

```shell
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
    bind my.awesomegame.com:443 ssl no-sslv3 no-tlsv10 crt /etc/letsencrypt/live/my.awesomegame.com>/my.awesomegame.com.pem
    server localhost 127.0.0.1:4001
    timeout client 10m
    timeout server 10m
    timeout connect 5m

listen evennia-secure-websocket
    bind my.awesomegame.com:4002 ssl no-sslv3 no-tlsv10 crt /etc/letsencrypt/live/my.awesomegame.com/my.awesomegame.com.pem
    server localhost 127.0.0.1:4002
    timeout client 10m
    timeout server 10m
    timeout connect 5m

```

## Putting it all together

Get back to the Evennia game dir and edit mygame/server/conf/settings.py. Add:

    WEBSERVER_INTERFACES = ['127.0.0.1']
    WEBSOCKET_CLIENT_INTERFACE = '127.0.0.1'

and

    WEBSOCKET_CLIENT_URL="wss://my.awesomegame.com:4002/"

Make sure to reboot (stop + start) evennia completely:

    evennia reboot


Finally you start the proxy:

```
sudo haproxy -f /path/to/the/above/haproxy.cfg

```

Make sure you can connect to your game from your browser and that you end up
with an `https://` page and can use the websocket webclient.

Once everything works you may want to start the proxy automatically and in the
background. Stop the proxy with `Ctrl-C` and make sure to uncomment the line `#
daemon` in the config file.

If you have no other proxies running on your server, you can copy your
haproxy.conf file to the system-wide settings:

    sudo cp /path/to/the/above/haproxy.cfg /etc/haproxy/

The proxy will now start on reload and you can control it with

    sudo service haproxy start|stop|restart|status

If you don't want to copy stuff into `/etc/` you can also run the haproxy purely
out of your current location by running it with `cron` on server restart. Open
the crontab again:

    sudo crontab -e

Add a new line to the end of the file:

    @reboot haproxy -f /path/to/the/above/haproxy.cfg

Save the file and haproxy should start up automatically when you reboot the
server. Next just restart the proxy manually a last time - with `daemon`
uncommented in the config file, it will now start as a background process.
