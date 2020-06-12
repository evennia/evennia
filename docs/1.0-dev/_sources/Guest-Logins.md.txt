# Guest Logins


Evennia supports *guest logins* out of the box. A guest login is an anonymous, low-access account and can be useful if you want users to have a chance to try out your game without committing to creating a real account.

Guest accounts are turned off by default. To activate, add this to your `game/settings.py` file:

    GUEST_ENABLED = True

Henceforth users can use `connect guest` (in the default command set) to login with a guest account. You may need to change your [Connection Screen](Connection-Screen) to inform them of this possibility. Guest accounts work differently from normal accounts - they are automatically *deleted* whenever the user logs off or the server resets (but not during a reload). They are literally re-usable throw-away accounts. 

You can add a few more variables to your `settings.py` file to customize your guests:

- `BASE_GUEST_TYPECLASS` - the python-path to the default [typeclass](Typeclasses) for guests. Defaults to `"typeclasses.accounts.Guest"`.
- `PERMISSION_GUEST_DEFAULT` - [permission level](Locks) for guest accounts. Defaults to `"Guests"`, which is the lowest permission level in the hierarchy.
- `GUEST_START_LOCATION` - the `#dbref` to the starting location newly logged-in guests should appear at. Defaults to `"#2` (Limbo).
- `GUEST_HOME` - guest home locations. Defaults to Limbo as well.
- `GUEST_LIST` - this is a list holding the possible guest names to use when entering the game. The length of this list also sets how many guests may log in at the same time. By default this is a list of nine names from `"Guest1"` to `"Guest9"`.
