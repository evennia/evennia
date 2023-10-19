# Security Hints and Practices

Hackers these days aren't discriminating, and their backgrounds range from bored teenagers to international intelligence agencies. Their scripts and bots endlessly crawl the web, looking for vulnerable systems they can break into. Who owns the system is irrelevant-- it doesn't matter if it belongs to you or the Pentagon, the goal is to take advantage of poorly-secured systems and see what resources can be controlled or stolen from them.

If you're considering deploying to a cloud-based host, you have a vested interest in securing your applications-- you likely have a credit card on file that your host can freely bill. Hackers pegging your CPU to mine cryptocurrency or saturating your network connection to participate in a botnet or send spam can run up your hosting bill, get your service suspended or get your address/site
blacklisted by ISPs. It can be a difficult legal or political battle to undo this damage after the
fact.

As a developer about to expose a web application to the threat landscape of the modern internet,
here are a few tips to consider to increase the security of your Evennia install.

## Know your logs
In case of emergency, check your logs! By default they are located in the `server/logs/` folder.
Here are some of the more important ones and why you should care:

* `http_requests.log` will show you what HTTP requests have been made against Evennia's built-in webserver (TwistedWeb). This is a good way to see if people are innocuously browsing your site or trying to break it through code injection.
* `portal.log` will show you various networking-related information. This is a good place to check for odd or unusual types or amounts of connections to your game, or other networking-related issues-- like when users are reporting an inability to connect.
* `server.log` is the MUX administrator's best friend. Here is where you'll find information pertaining to who's trying to break into your system by guessing at passwords, who created what objects, and more. If your game fails to start or crashes and you can't tell why, this is the first place you should look for answers. Security-related events are prefixed with an `[SS]` so when there's a problem you might want to pay special attention to those.

## Disable development/debugging options

There are a few Evennia/Django options that are set when you first create your game to make it more obvious to you where problems arise. These options should be disabled before you push your game into production-- leaving them on can expose variables or code someone with malicious intent can easily abuse to compromise your environment. 

In `server/conf/settings.py`:

    # Disable Django's debug mode
    DEBUG = False
    # Disable the in-game equivalent
    IN_GAME_ERRORS = False
    # If you've registered a domain name, force Django to check host headers. Otherwise leave this as-is.
    # Note the leading period-- it is not a typo!
    ALLOWED_HOSTS = ['.example.com']

## Handle user-uploaded images with care

If you decide to allow users to upload their own images to be served from your site, special care must be taken. Django will read the file headers to confirm it's an image (as opposed to a document or zip archive), but [code can be injected into an image file](https://insinuator.net/2014/05/django-image-validation-vulnerability/) *after* the headers that can be interpreted as HTML and/or give an attacker a web shell through which they can access
other filesystem resources.

[Django has a more comprehensive overview of how to handle user-uploaded files](https://docs.djangoproject.com/en/dev/topics/security/#user-uploaded-content-security), but
in short you should take care to do one of two things: 

* Serve all user-uploaded assets from a *separate* domain or CDN (*not* a subdomain of the one you already have!). For example, you may be browsing `reddit.com` but note that all the user-submitted images are being served from the `redd.it` domain. There are both security and performance benefits to this (webservers tend to load local resources one-by-one, whereas they will request external resources in bulk).
* If you don't want to pay for a second domain, don't understand what any of this means or can't be bothered with additional infrastructure, then simply reprocess user images upon receipt using an image library. Convert them to a different format, for example. *Destroy the originals!*

## Disable the web interface (if you only want telnet)

The web interface allows visitors to see an informational page as well as log into a browser-based telnet client with which to access Evennia. It also provides authentication endpoints against which an attacker can attempt to validate stolen lists of credentials to see which ones might be shared by your users. Django's security is robust, but if you don't want/need these features and fully intend
to force your users to use traditional clients to access your game, you might consider disabling
either/both to minimize your attack surface.

In `server/conf/settings.py`:

    # Disable the Javascript webclient
    WEBCLIENT_ENABLED = False
    # Disable the website altogether
    WEBSERVER_ENABLED = False

## Change your ssh port

Automated attacks will often target port 22 seeing as how it's the standard port for SSH traffic. Also, many public wifi hotspots block ssh traffic over port 22 so you might not be able to access your server from these locations if you like to work remotely or don't have a home internet connection. 

If you don't intend on running a website or securing it with TLS, you can mitigate both problems by changing the port used for ssh to 443, which most/all hotspot providers assume is HTTPS traffic and allows through. 

(Ubuntu) In /etc/ssh/sshd_config, change the following variable:

    # What ports, IPs and protocols we listen for
    Port 443

Save, close, then run the following command:

    sudo service ssh restart

## Set up a firewall

Ubuntu users can make use of the simple ufw utility. Anybody else can use iptables.

    # Install ufw (if not already)
    sudo apt-get install ufw

UFW's default policy is to deny everything. We must specify what we want to allow through our firewall.

    # Allow terminal connections to your game
    sudo ufw allow 4000/tcp
    # Allow browser connections to your website
    sudo ufw allow 4001/tcp

Use ONE of the next two commands depending on which port your ssh daemon is listening on:

    sudo ufw allow 22/tcp
    sudo ufw allow 443/tcp

Finally:

    sudo ufw enable

Now the only ports open will be your administrative ssh port (whichever you chose), and Evennia on 4000-4001.

## Use an external webserver / proxy

There are some benefits to deploying a _proxy_ in front of your Evennia server; notably it means you can serve Evennia website and webclient data from an HTTPS: url (with encryption). Any proxy can be used, for example: 

    -[HaProxy](./Config-HAProxy.md)
    -[Apache as a proxy](./Config-Apache-Proxy.md)
    - Nginx 
    - etc.