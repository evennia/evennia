# Internationalization


*Internationalization* (often abbreviated *i18n* since there are 18 characters between the first "i"
and the last "n" in that word) allows Evennia's core server to return texts in other languages than
English - without anyone having to edit the source code. Take a look at the `locale` directory of
the Evennia installation, there you will find which languages are currently supported.

## Changing server language

Change language by adding the following to your `mygame/server/conf/settings.py` file:

```python
    USE_I18N = True
    LANGUAGE_CODE = 'en'
```

Here `'en'` should be changed to the abbreviation for one of the supported languages found in
`locale/`. Restart the server to activate i18n. The two-character international language codes are
found [here](http://www.science.co.il/Language/Codes.asp).

> Windows Note: If you get errors concerning `gettext` or `xgettext` on Windows, see the [Django
documentation](https://docs.djangoproject.com/en/1.7/topics/i18n/translation/#gettext-on-windows). A
self-installing and up-to-date version of gettext for Windows (32/64-bit) is available on
[Github](https://github.com/mlocati/gettext-iconv-windows).

## Translating Evennia

> **Important Note:** Evennia offers translations of hard-coded strings in the server, things like
"Connection closed" or "Server restarted", strings that end users will see and which game devs are
not supposed to change on their own. Text you see in the log file or on the command line (like error
messages) are generally *not* translated (this is a part of Python).

> In addition, text in default Commands and in default Typeclasses will *not* be translated by
switching *i18n* language. To translate Commands and Typeclass hooks you must overload them in your
game directory and translate their returns to the language you want. This is because from Evennia's
perspective, adding *i18n* code to commands tend to add complexity to code that is *meant* to be
changed anyway. One of the goals of Evennia is to keep the user-changeable code as clean and easy-
to-read as possible.

If you cannot find your language in `evennia/locale/` it's because noone has translated it yet.
Alternatively you might have the language but find the translation bad ... You are welcome to help
improve the situation!

To start a new translation you need to first have cloned the Evennia repositry with GIT and
activated a python virtualenv as described on the [Setup Quickstart](../Setup/Setup-Quickstart) page. You now
need to `cd` to the `evennia/` directory. This is *not* your created game folder but the main
Evennia library folder. If you see a folder `locale/` then you are in the right place. From here you
run:

     evennia makemessages <language-code>

where `<language-code>` is the [two-letter locale code](http://www.science.co.il/Language/Codes.asp)
for the language you want, like 'sv' for Swedish or 'es' for Spanish. After a moment it will tell
you the language has been processed.  For instance:

     evennia makemessages sv

If you started a new language a new folder for that language will have emerged in the `locale/`
folder. Otherwise the system will just have updated the existing translation with eventual new
strings found in the server. Running this command will not overwrite any existing strings so you can
run it as much as you want.

> Note: in Django, the `makemessages` command prefixes the locale name by the `-l` option (`...
makemessages -l sv` for instance).  This syntax is not allowed in Evennia, due to the fact that `-l`
is the option to tail log files.  Hence, `makemessages` doesn't use the `-l` flag.

Next head to `locale/<language-code>/LC_MESSAGES` and edit the `**.po` file you find there.  You can
edit this with a normal text editor but it is easiest if you use a special po-file editor from the
web (search the web for "po editor" for many free alternatives).

The concept of translating is simple, it's just a matter of taking the english strings you find in
the `**.po` file and add your language's translation best you can. The `**.po` format (and many
supporting editors) allow you to mark translations as "fuzzy". This tells the system (and future
translators) that you are unsure about the translation, or that you couldn't find a translation that
exactly matched the intention of the original text. Other translators will see this and might be
able to improve it later.
Finally, you need to compile your translation into a more efficient form. Do so from the `evennia`
folder
again:

    evennia compilemessages

This will go through all languages and create/update compiled files (`**.mo`) for them. This needs
to be done whenever a `**.po` file is updated.

When you are done, send the `**.po` and `*.mo` file to the Evennia developer list (or push it into
your own repository clone) so we can integrate your translation into Evennia!