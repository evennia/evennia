# Internationalization

*Internationalization* (often abbreviated *i18n* since there are 18 characters
between the first "i" and the last "n" in that word) allows Evennia's core
server to return texts in other languages than English - without anyone having
to edit the source code.

Language-translations are done by volunteers, so support can vary a lot
depending on when a given language was last updated. Below are all languages
(besides English) with some level of support. Generally, any language not
updated after May 2021 will be missing some translations.

```eval_rst

+---------------+----------------------+--------------+
| Language Code | Language             | Last updated |
+===============+======================+==============+
| es            | Spanish              | Aug 2019     |
+---------------+----------------------+--------------+
| fr            | French               | Nov 2018     |
+---------------+----------------------+--------------+
| it            | Italian              | Feb 2015     |
+---------------+----------------------+--------------+
| ko            | Korean (simplified)  | Sep 2019     |
+---------------+----------------------+--------------+
| la            | Latin                | Feb 2021     |
+---------------+----------------------+--------------+
| pl            | Polish               | Feb 2019     |
+---------------+----------------------+--------------+
| pt            | Portugese            | Dec 2015     |
+---------------+----------------------+--------------+
| ru            | Russian              | Apr 2020     |
+---------------+----------------------+--------------+
| sv            | Swedish              | June 2021    |
+---------------+----------------------+--------------+
| zh            | Chinese (simplified) | May 2019     |
+---------------+----------------------+--------------+
```

Language translations are found in the [evennia/locale](github:evennia/locale/)
folder. Read below if you want to help improve an existing translation of
contribute a new one.

## Changing server language

Change language by adding the following to your `mygame/server/conf/settings.py`
file:

```python
    USE_I18N = True
    LANGUAGE_CODE = 'en'

```

Here `'en'` (the default English) should be changed to the abbreviation for one
of the supported languages found in `locale/` (and in the list above). Restart
the server to activate i18n.

```important::

    Even for a 'fully translated' language you will still see English text
    in many places when you start Evennia. This is because we expect you (the
    developer) to know English (you are reading this manual after all). So we
    translate *hard-coded strings that the end player may see* - things you
    can't easily change from your mygame/ folder. Outputs from Commands and
    Typeclasses are generally *not* translated, nor are console/log outputs.

```

```sidebar:: Windows users

    If you get errors concerning `gettext` or `xgettext` on Windows,
    see the `Django documentation <https://docs.djangoproject.com/en/3.2/topics/i18n/translation/#gettext-on-windows>`_
    A self-installing and up-to-date version of gettext for Windows (32/64-bit) is
    available on `Github <https://github.com/mlocati/gettext-iconv-windows>`_

```

## Translating Evennia

Translations are found in the core `evennia/` library, under
`evennia/evennia/locale/`. You must make sure to have cloned this repository
from [Evennia's github](github:evennia) before you can proceed.

If you cannot find your language in `evennia/evennia/locale/` it's because noone
has translated it yet.  Alternatively you might have the language but find the
translation bad ... You are welcome to help improve the situation!

To start a new translation you need to first have cloned the Evennia repositry
with GIT and activated a python virtualenv as described on the
[Setup Quickstart](../Setup/Setup-Quickstart) page.

Go to `evennia/evennia/` - that is, not your game dir, but inside the `evennia/`
repo itself. If you see the `locale/` folder you are in the right place.  Make
sure your `virtualenv` is active so the `evennia` command is available. Then run

     evennia makemessages --locale <language-code>

where `<language-code>` is the [two-letter locale code](http://www.science.co.il/Language/Codes.asp)
for the language you want to translate, like 'sv' for Swedish or 'es' for
Spanish. After a moment it will tell you the language has been processed.  For
instance:

     evennia makemessages --locale sv

If you started a new language, a new folder for that language will have emerged
in the `locale/` folder. Otherwise the system will just have updated the
existing translation with eventual new strings found in the server. Running this
command will not overwrite any existing strings so you can run it as much as you
want.

Next head to `locale/<language-code>/LC_MESSAGES` and edit the `**.po` file you
find there. You can edit this with a normal text editor but it is easiest if
you use a special po-file editor from the web (search the web for "po editor"
for many free alternatives), for example:

    - [gtranslator](https://wiki.gnome.org/Apps/Gtranslator)
    - [poeditor](https://poeditor.com/)

The concept of translating is simple, it's just a matter of taking the english
strings you find in the `**.po` file and add your language's translation best
you can. Once you are done, run

    `evennia compilemessages`

This will compile all languages. Check your language and also check back to your
`.po` file in case the process updated it - you may need to fill in some missing
header fields and should usually note who did the translation.

When you are done, make sure that everyone can benefit from your translation!
Make a PR against Evennia with the updated `**.po` file. Less ideally (if git is
not your thing) you can also attach it to a new post in our forums.

### Hints on translation

Many of the translation strings use `{ ... }` placeholders. This is because they
are to be used in `.format()` python operations. While you can change the
_order_  of these if it makes more sense in your language, you must _not_
translate the variables in these formatting tags - Python will look for them!

    Original: "|G{key} connected|n"
    Swedish:  "|G{key} anslöt|n"

You must also retain line breaks _at the start and end_ of a message, if any
(your po-editor should stop you if you don't). Try to also end with the same
sentence delimiter (if that makes sense in your language).

    Original: "\n(Unsuccessfull tried '{path}')."
    Swedish: "\nMisslyckades med att nå '{path}')."

Finally, try to get a feel for who a string is for. If a special technical term
is used it may be more confusing than helpful to translate it, even if it's
outside of a `{...}` tag. Even though the result is a mix of your language and
English, clarity is more important. Many languages may also use the English term
normally and reaching for a translation may make the result sound awkward
instead.

    Original: "\nError loading cmdset: No cmdset class '{classname}' in '{path}'.
               \n(Traceback was logged {timestamp})"
    Swedish:  "Fel medan cmdset laddades: Ingen cmdset-klass med namn '{classname}' i {path}.
               \n(Traceback loggades {timestamp})"
