# RSS


[RSS](http://en.wikipedia.org/wiki/RSS) is a format for easily tracking updates on websites. The
principle is simple - whenever a site is updated, a small text file is updated. An RSS reader can
then regularly go online, check this file for updates and let the user know what's new.

Evennia allows for connecting any number of RSS feeds to any number of in-game channels. Updates to
the feed will be conveniently echoed to the channel. There are many potential uses for this: For
example the MUD might use a separate website to host its forums. Through RSS, the players can then
be notified when new posts are made. Another example is to let everyone know you updated your dev
blog. Admins might also want to track the latest Evennia updates through our own RSS feed
[here](http://code.google.com/feeds/p/evennia/updates/basic).

## Configuring RSS

To use RSS, you first need to install the [feedparser](http://code.google.com/p/feedparser/) python
module.

    pip install feedparser

Next you activate RSS support in your config file by settting `RSS_ENABLED=True`.

Start/reload Evennia as a privileged user. You should now have a new command available, `@rss2chan`:

     @rss2chan <evennia_channel> = <rss_url>

### Setting up RSS, step by step

You can connect RSS to any Evennia channel, but for testing, let's set up a new channel "rss".

     @ccreate rss = RSS feeds are echoed to this channel!

Let's connect Evennia's code-update feed to this channel. The RSS url for evennia updates is
`https://github.com/evennia/evennia/commits/master.atom`, so let's add that:

     @rss2chan rss = https://github.com/evennia/evennia/commits/master.atom

That's it, really. New Evennia updates will now show up as a one-line title and link in the channel.
Give the `@rss2chan` command on its own to show all connections. To remove a feed from a channel,
you specify the connection again (use the command to see it in the list) but add the `/delete`
switch:

     @rss2chan/delete rss = https://github.com/evennia/evennia/commits/master.atom

You can connect any number of RSS feeds to a channel this way. You could also connect them to the
same channels as [IRC](./IRC) to have the feed echo to external chat channels as well.
