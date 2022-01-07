# Email-based login system

Evennia contrib - Griatch 2012

This is a variant of the login system that requires an email-address
instead of a username to login.

This used to be the default Evennia login before replacing it with a
more standard username + password system (having to supply an email
for some reason caused a lot of confusion when people wanted to expand
on it. The email is not strictly needed internally, nor is any
confirmation email sent out anyway).

## Installation

To your settings file, add/edit the line:

```python
CMDSET_UNLOGGEDIN = "contrib.base_systems.email_login.UnloggedinCmdSet"
CONNECTION_SCREEN_MODULE = "contrib.base_systems.email_login.connection_screens"

```

That's it. Reload the server and reconnect to see it.

## Notes:

If you want to modify the way the connection screen looks, point
`CONNECTION_SCREEN_MODULE` to your own module. Use the default as a
guide (see also Evennia docs).


----

<small>This document page is generated from `evennia/contrib/base_systems/email_login/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
