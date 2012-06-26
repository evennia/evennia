Making your game available online
=================================

Evennia development can be made also without any internet connection
(except to download updates). At some point however, you are likely to
want to make your game visible online, either as part of making it
public or to allow other developers or beta testers access to it.

Using your own computer as a server
-----------------------------------

By far the simplest and probably cheapest option. Evennia will run on
your own, home computer. Moreover, since Evennia is its own web server,
you don't need to install anything extra to also run its website.

**Advantages**

-  Free (except for internet cost and electrical bill)
-  Full control over the server/hardware (it sits right there!)
-  Easy to set up.
-  Also suitable for quick setups - e.g. to briefly show off results to
   your collaborators.

**Disadvantages**

-  You need a good internet connection, ideally without any
   upload/download limits/costs.
-  If you want to run a full game this way, your computer needs to
   always be on. It could be noisy, and as mentioned, the electrical
   bill is worth considering.
-  No support or safety - if your house burns down, so will your game.
   Also, you are yourself responsible for backups etc (some would
   consider this an advantage).
-  Home IP numbers are often dynamically allocated, so for permanent
   online time you need to set up a DNS to always re-point to the right
   place (see below).

Set up your own machine as a server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Making Evennia available from your own machine is mainly a matter of
configuring eventual firewalls to let Evennia's ports through. With
Evennia running, note which ports it is using (defaults are 4000 for
telnet and 8000 for webclient, we assume them below).

#. Go to `http://www.whatismyip.com/ <http://www.whatismyip.com/>`_ (or
   similar site). They should tell you which IP address you are
   connecting from, e.g. ``230.450.0.222``.
#. In your web browser, go to ``http://230.450.0.222:8000``, where the
   last ``:8000`` is the webclient port Evennia uses. If you see
   Evennia's website and can connect to the webclient - -congrats,
   that's it! Try to connect with a traditional MUD-client to the telnet
   port too, just to make sure.
#. Most likely you won't see the Evennia website right away though. This
   is probably because you have a firewall blocking the ports we need.
   There could also be a hardware-router between your computer and the
   Internet - in that case the IP address we see "from the outside" is
   actually the router's IP, not that of your computer on your local
   network.

   -  You need to let Evennia data out through your router/firewall. How
      you do that varies with manufacturer and software. But in
      principle you should look for something called "Port forwarding"
      or similar. You want to route port 8000/4000 from your computer to
      an "outgoing port" that the world can see. That latter port does
      *not* have to have the same number as the internal port! For
      example, you might want to connect port 8000 to an outgoing port
      80 - this is the port HTTP requests use and web browsers
      automatically look for. If you use port 80 you won't have to
      specify the port number in the url of your browser. If you run
      other web servers on your machine, that could be an issue though.
   -  I found that I had to reboot my router for this to take effect, so
      worth trying if you still cannot get to the Evennia website
      through your browser.

#. At this point you should be able to invite people to play your game
   on ``http://230.450.0.222:8000`` or via telnet to ``230.450.0.222``
   on port ``4000``.

A complication with using a specific IP address like this is that your
home IP might not remain the same. Many ISPs (Internet Service
Providers) allocates a dynamic IP to you which could change at any time.
When that happens, that IP you told people to go to will be worthless.
Also, that long string of numbers is not very pretty, is it? It's hard
to remember and not easy to use in marketing your game. What you need is
to alias it to a more sensible domain name - an alias that follows you
around also when the IP changes.

#. To set up a domain name alias, we recommend starting with a free
   domain name from `FreeDNS <http://freedns.afraid.org/>`_. Once you
   register there (it's free) you have access to tens of thousands
   domain names that people have "donated" to allow you to use for your
   own sub domain. For example, ``strangled.net`` is one of those
   available domains. So tying our IP address to ``strangled.net`` using
   the subdomain ``evennia`` would mean that one could henceforth direct
   people to
   `http://evennia.strangled.net:8000 <http://evennia.strangled.net:8000>`_
   for their gaming needs - far easier to remember!
#. So how do we make this new, nice domain name follow us also if our IP
   changes? For this we need to set up a little program on our computer.
   It will check whenever our ISP decides to change our IP and tell
   FreeDNS that. There are many alternatives to be found from FreeDNS:s
   homepage, one that works on multiple platforms is
   `inadyn <http://www.inatech.eu/inadyn/>`_. Get it from their page or,
   in Linux, through something like

::

     apt-get install inadyn

#. Next, you login to your account on FreeDNS and go to the
   `Dynamic <http://freedns.afraid.org/dynamic/>`_ page. You should have
   a list of your subdomains. Click the ``Direct URL`` link and you'll
   get a page with a text message. Ignore that and look at the URL of
   the page. It should be ending in a lot of random letters. Everything
   after the question mark is your unique "hash". Copy this string.
#. You now start inadyn with the following command (Linux):

::

    inadyn --dyndns_system default@freedns.afraid.org -a <my.domain>,<hash> &

    where ``<my.domain>`` would be ``evennia.strangled.net`` and
    ``<hash>`` the string of numbers we copied from FreeDNS. The ``&``
    means we run in the background (might not be valid in other
    operating systems). ``inadyn`` will henceforth check for changes
    every 60 seconds. You should put the ``inadyn`` command string in a
    startup script somewhere so it kicks into gear whenever your
    computer starts.

Remote hosting
--------------

Your normal "web hotel" will probably not be enough to run Evennia. A
web hotel is normally aimed at a very specific usage - delivering web
pages, at the most with some dynamic content. The "Python scripts" they
refer to on their home pages are usually only intended to be CGI-like
scripts launched by their webserver. Even if they allow you shell access
(so you can install the Evennia dependencies in the first place),
resource usage will likely be very restricted. Running a full-fledged
game server like Evennia will probably be shunned upon or be outright
impossible. If you are unsure, contact your web hotel and ask about
their policy on you running third-party servers that will want to open
custom ports.

The options you probably need to look for are *shell account services*
or *VPS:es*. A "Shell account" service means that you get a shell
account on a server and can log in like any normal user. By contrast, a
*VPS* (Virtual Private Server) service usually means that you get
``root`` access, but in a virtual machine.

**Advantages**

-  Shell accounts/VPS offer more flexibility than your average web hotel
   - it's the ability to log onto a shared computer away from home.
-  Usually runs a Linux flavor, making it easy to install Evennia.
-  Support. You don't need to maintain the server hardware. If your
   house burns down, at least your game stays online. Many services
   guarantee a certain level of up-time and might also do regular
   backups for you (this varies).
-  Gives a fixed domain name, so no need to mess with IP addresses.

**Disadvantages**

-  Might be pretty expensive (more so than a web hotel)
-  Linux flavors might feel unfamiliar to users not used to ssh/PuTTy
   and the Linux command line.
-  You are probably sharing the server with many others, so you are not
   completely in charge. CPU usage might be limited. Also, if the server
   people decides to take the server down for maintenance, you have no
   choice but to sit it out (but you'll hopefully be warned ahead of
   time).

Set up Evennia on a remote shell account/VPS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Assuming you know how to connect to your account over ssh/PuTTy you
should be able to follow the `Getting Started <GettingStarted.html>`_
instructions normally. Ports might be an issue, so make sure you know
which ports are available to use.

If you don't have root access in a virtual machine (but just a normal
user-shell account), you will probably *not* have all resources easily
available. You need root to use ``apt-get`` for example. In that case
you should be able set up a virtualenv install instead, see the last
section of `Getting Started <GettingStarted.html>`_ for more info.

To find commercial solutions, just scour the web for shell access/VPS in
your region. One user has for example reported some success with
`Webfaction <http://www.webfaction.com/>`_.

Worth checking out is a free hosting offer especially aimed at MUDs
`here <http://zeno.biyg.org/portal.php>`_. An account and some activity
at `MUDbytes <http://www.mudbytes.net>`_ is required (that's a good
forum to join anyway if you are interested in MUDs). On this
mud-specific server you can reserve ports to use as well. From their
page it's however unclear which resources are available (only gcc is
listed), so one probably needs to use a virtualenv setup to get all
dependencies.
