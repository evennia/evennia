# Banning


Whether due to abuse, blatant breaking of your rules, or some other reason, you will eventually find
no other recourse but to kick out a particularly troublesome player. The default command set has
admin tools to handle this, primarily `ban`, `unban`, and `boot`.

## Creating a ban

Say we have a troublesome player "YouSuck" - this is a person that refuses common courtesy - an
abusive
and spammy account that is clearly created by some bored internet hooligan only to cause grief. You
have tried to be nice. Now you just want this troll gone.

### Name ban

The easiest recourse is to block the account YouSuck from ever connecting again.

     ban YouSuck

This will lock the name YouSuck (as well as 'yousuck' and any other capitalization combination), and
next time they try to log in with this name the server will not let them!

You can also give a reason so you remember later why this was a good thing (the banned account will
never see this)

     ban YouSuck:This is just a troll.

If you are sure this is just a spam account, you might even consider deleting the player account
outright:

     account/delete YouSuck

Generally, banning the name is the easier and safer way to stop the use of an account -- if you
change your mind you can always remove the block later whereas a deletion is permanent.

### IP ban

Just because you block YouSuck's name might not mean the trolling human behind that account gives
up. They can just create a new account YouSuckMore and be back at it. One way to make things harder
for them is to tell the server to not allow connections from their particular IP address.

First, when the offending account is online, check which IP address they use. This you can do with
the `who` command, which will show you something like this:

     Account Name     On for     Idle     Room     Cmds     Host
     YouSuckMore      01:12      2m       22       212      237.333.0.223

The "Host" bit is the IP address from which the account is connecting. Use this to define the ban
instead of the name:

     ban 237.333.0.223

This will stop YouSuckMore connecting from their computer. Note however that IP address might change
easily - either due to how the player's Internet Service Provider operates or by the user simply
changing computers. You can make a more general ban by putting asterisks `*` as wildcards for the
groups of three digits in the address. So if you figure out that !YouSuckMore mainly connects from
237.333.0.223, 237.333.0.225, and 237.333.0.256 (only changes in their subnet), it might be an idea
to put down a ban like this to include any number in that subnet:

     ban 237.333.0.*

You should combine the IP ban with a name-ban too of course, so the account YouSuckMore is truly
locked regardless of where they connect from.

Be careful with too general IP bans however (more asterisks above). If you are unlucky you could be
blocking out innocent players who just happen to connect from the same subnet as the offender.

## Booting

YouSuck is not really noticing all this banning yet though - and won't until having logged out and
trying to log back in again. Let's help the troll along.

     boot YouSuck

Good riddance. You can give a reason for booting too (to be echoed to the player before getting
kicked out).

     boot YouSuck:Go troll somewhere else.

### Lifting a ban

Use the `unban` (or `ban`) command without any arguments and you will see a list of all currently
active bans:

    Active bans
    id   name/ip       date                      reason
    1    yousuck       Fri Jan 3 23:00:22 2020   This is just a Troll.
    2    237.333.0.*   Fri Jan 3 23:01:03 2020   YouSuck's IP.

Use the `id` from this list to find out which ban to lift.

     unban 2
      
    Cleared ban 2: 237.333.0.*

## Summary of abuse-handling tools

Below are other useful commands for dealing with annoying players.

- **who** -- (as admin) Find the IP of a account. Note that one account can be connected to from
multiple IPs depending on what you allow in your settings.
- **examine/account thomas** -- Get all details about an account. You can also use `*thomas` to get
the account. If not given, you will get the *Object* thomas if it exists in the same location, which
is not what you want in this case.
- **boot thomas**  -- Boot all sessions of the given account name.
- **boot 23** -- Boot one specific client session/IP by its unique id.
- **ban** -- List all bans (listed with ids)
- **ban thomas** -- Ban the user with the given account name
- **ban/ip `134.233.2.111`** -- Ban by IP
- **ban/ip `134.233.2.*`** -- Widen IP ban
- **ban/ip `134.233.*.*`** -- Even wider IP ban
- **unban 34** -- Remove ban with id #34

- **cboot mychannel = thomas** -- Boot a subscriber from a channel you control
- **clock mychannel = control:perm(Admin);listen:all();send:all()** -- Fine control of access to
your channel using [lock definitions](./Locks.md).

Locking a specific command (like `page`) is accomplished like so:
1. Examine the source of the command. [The default `page` command class](
https://github.com/evennia/evennia/blob/master/evennia/commands/default/comms.py#L686) has the lock
string **"cmd:not pperm(page_banned)"**. This means that unless the player has the 'permission'
"page_banned" they can use this command. You can assign any lock string to allow finer customization
in your commands. You might look for the value of an [Attribute](./Attributes.md) or [Tag](./Tags.md), your
current location etc.
2. **perm/account thomas = page_banned** -- Give the account the 'permission' which causes (in this
case) the lock to fail.

- **perm/del/account thomas = page_banned** -- Remove the given permission

- **tel thomas = jail** -- Teleport a player to a specified location or #dbref
- **type thomas = FlowerPot** -- Turn an annoying player into a flower pot (assuming you have a
`FlowerPot` typeclass ready)
- **userpassword thomas = fooBarFoo** -- Change a user's password
- **account/delete thomas** -- Delete a player account (not recommended, use **ban** instead)

- **server** -- Show server statistics, such as CPU load, memory usage, and how many objects are
cached
- **time** -- Gives server uptime, runtime, etc
- **reload** -- Reloads the server without disconnecting anyone
- **reset** -- Restarts the server, kicking all connections
- **shutdown** -- Stops the server cold without it auto-starting again
- **py** -- Executes raw Python code, allows for direct inspection of the database and account
objects on the fly. For advanced users.


**Useful Tip:** `evennia changepassword <username>` entered into the command prompt will reset the
password of any account, including the superuser or admin accounts. This is a feature of Django.
