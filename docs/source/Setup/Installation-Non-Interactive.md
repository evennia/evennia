# Non-interactive setup

The first ime you run `evennia start` (just after having created the database), you will be asked
to interactively insert the superuser username, email and password. If you are deploying Evennia 
as part of an automatic build script, you don't want to enter this information manually.

You can have the superuser be created automatically by passing environment variables to your 
build script:

- `EVENNIA_SUPERUSER_USERNAME`
- `EVENNIA_SUPERUSER_PASSWORD`
- `EVENNIA_SUPERUSER_EMAIL` is optional. If not given, empty string is used.
 
These envvars will only be used on the _very first_ server start and then ignored. For example:

```
EVENNIA_SUPERUSER_USERNAME=myname EVENNIA_SUPERUSER_PASSWORD=mypwd evennia start

```