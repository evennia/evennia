# Online Setup


Evennia development can be made without any Internet connection beyond fetching updates. At some
point however, you are likely to want to make your game visible online, either as part opening it to
the public or to allow other developers or beta testers access to it.

## Connecting from the outside

Accessing your Evennia server from the outside is not hard on its own. Any issues are usually due to
the various security measures your computer, network or hosting service has. These will generally
(and correctly) block outside access to servers on your machine unless you tell them otherwise.

We will start by showing how to host your server on your own local computer. Even if you plan to
host your "real" game on a remote host later, setting it up locally is useful practice. We cover
remote hosting later in this document.

Out of the box, Evennia uses three ports for outward communication. If your computer has a firewall,
these should be open for in/out communication (and only these, other ports used by Evennia are
internal to your computer only).
 - `4000`, telnet, for traditional mud clients
 - `4001`, HTTP for the website)
 - `4002`, websocket, for the web client

Evennia will by default accept incoming connections on all interfaces (`0.0.0.0`) so in principle
anyone knowing the ports to use and has the IP address to your machine should be able to connect to
your game.

 - Make sure Evennia is installed and that you have activated the virtualenv. Start the server with
`evennia start --log`. The `--log` (or `-l`) will make sure that the logs are echoed to the
terminal.
> Note: If you need to close the log-view, use `Ctrl-C`. Use just `evennia --log` on its own to
start tailing the logs again.
 - Make sure you can connect with your web browser to `http://localhost:4001` or, alternatively,
`http:127.0.0.1:4001` which is the same thing. You should get your Evennia web site and be able to
play the game in the web client. Also check so that you can connect with a mud client to host
`localhost`, port `4000` or host `127.0.0.1`, port `4000`.
- [Google for "my ip"](https://www.google.se/search?q=my+ip) or use any online service to figure out
what your "outward-facing" IP address is. For our purposes, let's say your outward-facing IP is
`203.0.113.0`.
 - Next try your outward-facing IP by opening `http://203.0.113.0:4001` in a browser. If this works,
that's it! Also try telnet, with the server set to `203.0.113.0` and port `4000`. However, most
likely it will *not* work. If so, read on.
 - If your computer has a firewall, it may be blocking the ports we need (it may also block telnet
overall). If so, you need to open the outward-facing ports to in/out communication. See the
manual/instructions for your firewall software on how to do this. To test you could also temporarily
turn off your firewall entirely to see if that was indeed the problem.
 - Another common problem for not being able to connect is that you are using a hardware router
(like a wifi router). The router sits 'between' your computer and the Internet. So the IP you find
with Google is the *router's* IP, not that of your computer. To resolve this you need to configure
your router to *forward* data it gets on its ports to the IP and ports of your computer sitting in
your private network. How to do this depends on the make of your router; you usually configure it
using a normal web browser. In the router interface, look for "Port forwarding" or maybe "Virtual
server". If that doesn't work, try to temporarily wire your computer directly to the Internet outlet
(assuming your computer has the ports for it). You'll need to check for your IP again. If that
works, you know the problem is the router.

> Note: If you need to reconfigure a router, the router's Internet-facing ports do *not* have to
have to have the same numbers as your computer's (and Evennia's) ports! For example, you might want
to connect Evennia's outgoing port 4001 to an outgoing router port 80 - this is the port HTTP
requests use and web browsers automatically look for - if you do that you could go to
`http://203.0.113.0` without having to add the port at the end. This would collide with any other
web services you are running through this router though.

### Settings example

You can connect Evennia to the Internet without any changes to your settings. The default settings
are easy to use but are not necessarily the safest. You can customize your online presence in your
[settings file](./Server-Conf#settings-file). To have Evennia recognize changed port settings you have
to do a full `evennia reboot` to also restart the Portal and not just the Server component.

Below is an example of a simple set of settings, mostly using the defaults. Evennia will require
access to five computer ports, of which three (only) should be open to the outside world. Below we
continue to assume that our server address is `203.0.113.0`.

```python
# in mygame/server/conf/settings.py

SERVERNAME = "MyGame"

# open to the internet: 4000, 4001, 4002
# closed to the internet (internal use): 4005, 4006
TELNET_PORTS = [4000]
WEBSOCKET_CLIENT_PORT = 4002
WEBSERVER_PORTS = [(4001, 4005)]
AMP_PORT = 4006

# Optional - security measures limiting interface access
# (don't set these before you know things work without them)
TELNET_INTERFACES = ['203.0.113.0']
WEBSOCKET_CLIENT_INTERFACE = '203.0.113.0'
ALLOWED_HOSTS = [".mymudgame.com"]

# uncomment if you want to lock the server down for maintenance.
# LOCKDOWN_MODE = True

```

Read on for a description of the individual settings.

### Telnet

```python
# Required. Change to whichever outgoing Telnet port(s)
# you are allowed to use on your host.
TELNET_PORTS = [4000]
# Optional for security. Restrict which telnet
# interfaces we should accept. Should be set to your
# outward-facing IP address(es). Default is ´0.0.0.0´
# which accepts all interfaces.
TELNET_INTERFACES = ['0.0.0.0']
```

The `TELNET_*` settings are the most important ones for getting a traditional base game going. Which
IP addresses you have available depends on your server hosting solution (see the next sections).
Some hosts will restrict which ports you are allowed you use so make sure to check.

### Web server

```python
# Required. This is a list of tuples
# (outgoing_port, internal_port). Only the outgoing
# port should be open to the world!
# set outgoing port to 80 if you want to run Evennia
# as the only web server on your machine (if available).
WEBSERVER_PORTS = [(4001, 4005)]
# Optional for security. Change this to the IP your
# server can be reached at (normally the same
# as TELNET_INTERFACES)
WEBSERVER_INTERFACES = ['0.0.0.0']
# Optional for security. Protects against
# man-in-the-middle attacks. Change  it to your server's
# IP address or URL when you run a production server.
ALLOWED_HOSTS = ['*']
```

The web server is always configured with two ports at a time. The *outgoing* port (`4001` by
default) is the port external connections can use. If you don't want users to have to specify the
port when they connect, you should set this to `80` - this however only works if you are not running
any other web server on the machine.
The *internal* port (`4005` by default) is used internally by Evennia to communicate between the
Server and the Portal. It should not be available to the outside world. You usually only need to
change the outgoing port unless the default internal port is clashing with some other program.

### Web client

```python
# Required. Change this to the main IP address of your server.
WEBSOCKET_CLIENT_INTERFACE = '0.0.0.0'
# Optional and needed only if using a proxy or similar. Change
# to the IP or address where the client can reach
# your server. The ws:// part is then required. If not given, the client
# will use its host location.
WEBSOCKET_CLIENT_URL = ""
# Required. Change to a free port for the websocket client to reach
# the server on. This will be automatically appended
# to WEBSOCKET_CLIENT_URL by the web client.
WEBSOCKET_CLIENT_PORT = 4002
```

The websocket-based web client needs to be able to call back to the server, and these settings must
be changed for it to find where to look. If it cannot find the server you will get an warning in
your browser's Console (in the dev tools of the browser), and the client will revert to the AJAX-
based of the client instead, which tends to be slower.

### Other ports

```python
# Optional public facing. Only allows SSL connections (off by default).
SSL_PORTS = [4003]
SSL_INTERFACES = ['0.0.0.0']
# Optional public facing. Only if you allow SSH connections (off by default).
SSH_PORTS = [4004]
SSH_INTERFACES = ['0.0.0.0']
# Required private. You should only change this if there is a clash
# with other services on your host. Should NOT be open to the
# outside world.
AMP_PORT = 4006
```

The `AMP_PORT` is required to work, since this is the internal port linking Evennia's [Server and
Portal](Portal-And-Server) components together. The other ports are encrypted ports that may be
useful for custom protocols but are otherwise not used.

### Lockdown mode

When you test things out and check configurations you may not want players to drop in on you.
Similarly, if you are doing maintenance on a live game you may want to take it offline for a while
to fix eventual problems without risking people connecting. To do this, stop the server with
`evennia stop` and add `LOCKDOWN_MODE = True` to your settings file. When you start the server
again, your game will only be accessible from localhost.

### Registering with the Evennia game directory

Once your game is online you should make sure to register it with the [Evennia Game
Index](http://games.evennia.com/). Registering with the index will help  people find your server,
drum up interest for your game and also shows people that Evennia is being used. You can do this
even if you are just starting development - if you don't give any telnet/web address it will appear
as _Not yet public_ and just be a teaser. If so, pick _pre-alpha_ as the development status.

To register, stand in your game dir, run

    evennia connections

and follow the instructions. See the [Game index page](./Evennia-Game-Index) for more details.

## SSL

SSL can be very useful for web clients. It will protect the credentials and gameplay of your users
over a web client if they are in a public place, and your websocket can also be switched to WSS for
the same benefit. SSL certificates used to cost money on a yearly basis, but there is now a program
that issues them for free with assisted setup to make the entire process less painful.

Options that may be useful in combination with an SSL proxy:

```
# See above for the section on Lockdown Mode.
# Useful for a proxy on the public interface connecting to Evennia on localhost.
LOCKDOWN_MODE = True

# Have clients communicate via wss after connecting with https to port 4001.
# Without this, you may get DOMException errors when the browser tries
# to create an insecure websocket from a secure webpage.
WEBSOCKET_CLIENT_URL = "wss://fqdn:4002"
```

### Let's Encrypt

[Let's Encrypt](https://letsencrypt.org) is a certificate authority offering free certificates to
secure a website with HTTPS. To get started issuing a certificate for your web server using Let's
Encrypt, see these links:

 - [Let's Encrypt - Getting Started](https://letsencrypt.org/getting-started/)
 - The [CertBot Client](https://certbot.eff.org/) is a program for automatically obtaining a
certificate, use it and maintain it with your website.

Also, on Freenode visit the #letsencrypt channel for assistance from the community. For an
additional resource, Let's Encrypt has a very active [community
forum](https://community.letsencrypt.org/).

[A blog where someone sets up Let's Encrypt](https://www.digitalocean.com/community/tutorials/how-
to-secure-apache-with-let-s-encrypt-on-ubuntu-16-04)

The only process missing from all of the above documentation is how to pass verification. This is
how Let's Encrypt verifies that you have control over your domain (not necessarily ownership, it's
Domain Validation (DV)). This can be done either with configuring a certain path on your web server
or through a TXT record in your DNS. Which one you will want to do is a personal preference, but can
also be based on your hosting choice. In a controlled/cPanel environment, you will most likely have
to use DNS verification.

## Relevant SSL Proxy Setup Information
- [HAProxy Config](./HAProxy-Config) - this is recommended for use with letsencrypt. This
page also has a more full description on how to set things up.
- [Apache webserver configuration](./Apache-Config) (optional)

## Hosting locally or remotely?

### Using your own computer as a server

What we showed above is by far the simplest and probably cheapest option: Run Evennia on your own
home computer. Moreover, since Evennia is its own web server, you don't need to install anything
extra to have a website.

**Advantages**
- Free (except for internet costs and the electrical bill).
- Full control over the server and hardware (it sits right there!).
- Easy to set up.
- Suitable for quick setups - e.g. to briefly show off results to your collaborators.

**Disadvantages**
- You need a good internet connection, ideally without any upload/download limits/costs.
- If you want to run a full game this way, your computer needs to always be on. It could be noisy,
and as mentioned, the electrical bill must be considered.
- No support or safety - if your house burns down, so will your game. Also, you are yourself
responsible for doing regular backups.
- Potentially not as easy if you don't know how to open ports in your firewall or router.
- Home IP numbers are often dynamically allocated, so for permanent online time you need to set up a
DNS to always re-point to the right place (see below).
- You are personally responsible for any use/misuse of your internet connection-- though unlikely
(but not impossible) if running your server somehow causes issues for other customers on the
network, goes against your ISP's terms of service (many ISPs insist on upselling you to a business-
tier connection) or you are the subject of legal action by a copyright holder, you may find your
main internet connection terminated as a consequence.

#### Setting up your own machine as a server

[The first section](./Online-Setup#connecting-from-the-outside) of this page describes how to do this
and allow users to connect to the IP address of your machine/router.

A complication with using a specific IP address like this is that your home IP might not remain the
same. Many ISPs (Internet Service Providers) allocates a *dynamic* IP to you which could change at
any time. When that happens, that IP you told people to go to will be worthless. Also, that long
string of numbers is not very pretty, is it? It's hard to remember and not easy to use in marketing
your game. What you need is to alias it to a more sensible domain name - an alias that follows you
around also when the IP changes.

1. To set up a domain name alias, we recommend starting with a free domain name from
[FreeDNS](http://freedns.afraid.org/). Once you register there (it's free) you have access to tens
of thousands domain names that people have "donated" to allow you to use for your own sub domain.
For example, `strangled.net` is one of those available domains. So tying our IP address to
`strangled.net` using the subdomain `evennia` would mean that one could henceforth direct people to
`http://evennia.strangled.net:4001` for their gaming needs - far easier to remember!
1. So how do we make this new, nice domain name follow us also if our IP changes? For this we need
to set up a little program on our computer. It will check whenever our ISP decides to change our IP
and tell FreeDNS that. There are many alternatives to be found from FreeDNS:s homepage, one that
works on multiple platforms is [inadyn](http://www.inatech.eu/inadyn/). Get it from their page or,
in Linux, through something like `apt-get install inadyn`.
1. Next, you login to your account on FreeDNS and go to the
[Dynamic](http://freedns.afraid.org/dynamic/) page. You should have a list of your subdomains. Click
the `Direct URL` link and you'll get a page with a text message. Ignore that and look at the URL of
the page. It should be ending in a lot of random letters. Everything after the question mark is your
unique "hash". Copy this string.
1. You now start inadyn with the following command (Linux):

    `inadyn --dyndns_system default@freedns.afraid.org -a <my.domain>,<hash> &`

 where `<my.domain>` would be `evennia.strangled.net` and `<hash>` the string of numbers we copied
from FreeDNS. The `&` means we run in the background (might not  be valid in other operating
systems). `inadyn` will henceforth check for changes every 60 seconds. You should put the `inadyn`
command string in a startup script somewhere so it kicks into gear whenever your computer starts.

### Remote hosting

Your normal "web hotel" will probably not be enough to run Evennia. A web hotel is normally aimed at
a very specific usage - delivering web pages, at the most with some dynamic content. The "Python
scripts" they refer to on their home pages are usually only intended to be CGI-like scripts launched
by their webserver. Even if they allow you shell access (so you can install the Evennia dependencies
in the first place), resource usage will likely be very restricted. Running a full-fledged game
server like Evennia will probably be shunned upon or be outright impossible.  If you are unsure,
contact your web hotel and ask about their policy on you running third-party servers that will want
to open custom ports.

The options you probably need to look for are *shell account services*, *VPS:es* or *Cloud
services*. A "Shell account" service means that you get a shell account on a server and can log in
like any normal user. By contrast, a *VPS* (Virtual Private Server) service usually means that you
get `root` access, but in a virtual machine. There are also *Cloud*-type services which allows for
starting up multiple virtual machines and pay for what resources you use.

**Advantages**
- Shell accounts/VPS/clouds offer more flexibility than your average web hotel - it's the ability to
log onto a shared computer away from home.
- Usually runs a Linux flavor, making it easy to install Evennia.
- Support. You don't need to maintain the server hardware. If your house burns down, at least your
game stays online. Many services guarantee a certain level of up-time and also do regular backups
for you. Make sure to check, some offer lower rates in exchange for you yourself being fully
responsible for your data/backups.
- Usually offers a fixed domain name, so no need to mess with IP addresses.
- May have the ability to easily deploy [docker](./Running-Evennia-in-Docker) versions of evennia
and/or your game.

**Disadvantages**
- Might be pretty expensive (more so than a web hotel). Note that Evennia will normally need at
least 100MB RAM and likely much more for a large production game.
- Linux flavors might feel unfamiliar to users not used to ssh/PuTTy and the Linux command line.
- You are probably sharing the server with many others, so you are not completely in charge. CPU
usage might be limited. Also, if the server people decides to take the server down for maintenance,
you have no choice but to sit it out (but you'll hopefully be warned ahead of time).

#### Installing Evennia on a remote server

Firstly, if you are familiar with server infrastructure, consider using [Docker](Running-Evennia-in-
Docker) to deploy your game to the remote server; it will likely ease installation and deployment.
Docker images may be a little confusing if you are completely new to them though.

If not using docker, and assuming you know how to connect to your account over ssh/PuTTy, you should
be able to follow the [Getting Started](./Getting-Started) instructions normally. You only need Python
and GIT pre-installed; these should both be available on any servers (if not you should be able to
easily ask for them to be installed). On a VPS or Cloud service you can install them yourself as
needed.

If `virtualenv` is not available and you can't get it, you can download it (it's just a single file)
from [the virtualenv pypi](https://pypi.python.org/pypi/virtualenv). Using `virtualenv` you can
install everything without actually needing to have further `root` access. Ports might be an issue,
so make sure you know which ports are available to use and reconfigure Evennia accordingly.

### Hosting options

To find commercial solutions, browse the web for "shell access", "VPS" or "Cloud services" in your
region. You may find useful offers for "low cost" VPS hosting on [Low End Box][7]. The associated
[Low End Talk][8] forum can be useful for health checking the many small businesses that offer
"value" hosting, and occasionally for technical suggestions.

There are all sorts of services available. Below are some international suggestions offered by
Evennia users:

Hosting name       |  Type          |  Lowest price  |  Comments
:--------------:|:-------:---------------
[silvren.com][1]   | Shell account | Free for MU*  | Private hobby provider so don't assume backups
or expect immediate support. To ask for an account, connect with a MUD client to iweb.localecho.net,
port 4201 and ask for "Jarin".
[Digital Ocean][2] | VPS | $5/month | You get a credit if you use the referral link
https://m.do.co/c/8f64fec2670c - if you do, once you've had it long enough to have paid $25 we will
get that as a referral bonus to help Evennia development.
[Amazon Web services][3] | Cloud | ~$5/month / on-demand | Free Tier first 12 months. Regions
available around the globe.
[Amazon Lightsail][9] | Cloud | $5/month | Free first month. AWS's new "fixed cost" offering.
[Genesis MUD hosting][4] | Shell account | $8/month | Dedicated MUD host with very limited memory
offerings. As for 2017, runs a 13 years old Python version (2.4) so you'd need to either convince
them to update or compile yourself. Note that Evennia needs *at least* the "Deluxe" package (50MB
RAM) and probably *a lot* higher for a production game. This host is *not* recommended for Evennia.
[Host1Plus][5] | VPS & Cloud | $4/month | $4-$8/month depending on length of sign-up period.
[Scaleway][6] | Cloud | &euro;3/month / on-demand | EU based (Paris, Amsterdam). Smallest option
provides 2GB RAM.
[Prgmr][10] | VPS | $5/month | 1 month free with a year prepay. You likely want some experience with
servers with this option as they don't have a lot of support.
[Linode][11] | Cloud | $5/month / on-demand | Multiple regions. Smallest option provides 1GB RAM
*Please help us expand this list.*

[1]: http:silvren.com
[2]: https://www.digitalocean.com/pricing
[3]: https://aws.amazon.com/pricing/
[4]: http://www.genesismuds.com/
[5]: https://www.host1plus.com/
[6]: https://www.scaleway.com/
[7]: https://lowendbox.com/
[8]: https://www.lowendtalk.com
[9]: https://amazonlightsail.com
[10]: https://prgmr.com/
[11]: https://www.linode.com/

## Cloud9

If you are interested in running Evennia in the online dev environment [Cloud9](https://c9.io/), you
can spin it up through their normal online setup using the Evennia Linux install instructions. The
one extra thing you will have to do is update `mygame/server/conf/settings.py` and add
`WEBSERVER_PORTS = [(8080, 4001)]`. This will then let you access the web server and do everything
else as normal.

Note that, as of December 2017, Cloud9 was re-released by Amazon as a service within their AWS cloud
service offering. New customers entitled to the 1 year AWS "free tier" may find it provides
sufficient resources to operate a Cloud9 development environment without charge.
https://aws.amazon.com/cloud9/

