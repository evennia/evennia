# Contributing


Wanna help out? Great! Here's how. 

## Spreading the word

Even if you are not keen on working on the server code yourself, just spreading the word is a big
help - it will help attract more people which leads to more feedback, motivation and interest.
Consider writing about Evennia on your blog or in your favorite (relevant) forum. Write a review
somewhere (good or bad, we like feedback either way). Rate it on places like [ohloh][ohloh]. Talk
about it to your friends ... that kind of thing.

## Donations

The best way to support Evennia is to become an [Evennia patron][patron]. Evennia is a free,
open-source project and any monetary donations you want to offer are completely voluntary. See it as
a way of announcing that you appreciate the work done - a tip of the hat! A patron donates a
(usually small) sum every month to show continued support.  If this is not your thing you can also
show your appreciation via a [one-time donation][donate] (this is a PayPal link but you don't need
PayPal yourself). 

## Help with Documentation

Evennia depends heavily on good documentation and we are always looking for extra eyes and hands to
improve it. Even small things such as fixing typos are a great help!

The documentation is a wiki and as long as you have a GitHub account you can edit it. It can be a
good idea to discuss in the chat or forums if you want to add new pages/tutorials. Otherwise, it
goes a long way just pointing out wiki errors so we can fix them (in an Issue or just over
chat/forum).

## Contributing through a forked repository

We always need more eyes and hands on the code. Even if you don't feel confident with tackling a
[bug or feature][issues], just correcting typos, adjusting formatting or simply *using* the thing
and reporting when stuff doesn't make sense helps us a lot.

The most elegant way to contribute code to Evennia is to use GitHub to create a *fork* of the
Evennia repository and make your changes to that. Refer to the [Forking Evennia](Version-Control#forking-evennia) version
control instructions for detailed instructions. 

Once you have a fork set up, you can not only work on your own game in a separate branch, you can
also commit your fixes to Evennia itself. Make separate branches for all Evennia additions you do -
don't edit your local `master` or `develop` branches directly. It will make your life a lot easier.
If you have a change that you think is suitable for the main Evennia repository, you issue a [Pull
Request][pullrequest]. This will let Evennia devs know you have stuff to share. Bug fixes should
generally be done against the `master` branch of Evennia, while new features/contribs should go into
the `develop` branch. If you are unsure, just pick one and we'll figure it out.
 
## Contributing with Patches

To help with Evennia development it's recommended to do so using a fork repository as described
above. But for small, well isolated fixes you are also welcome to submit your suggested Evennia
fixes/addendums as a [patch][patch].

You can include your patch in an Issue or a Mailing list post. Please avoid pasting the full patch
text directly in your post though, best is to use a site like [Pastebin](http://pastebin.com/) and
just supply the link. 

## Contributing with Contribs

While Evennia's core is pretty much game-agnostic, it also has a `contrib/` directory. The `contrib`
directory contains game systems that are specialized or useful only to certain types of games. Users
are welcome to contribute to the `contrib/` directory. Such contributions should always happen via a
Forked repository as described above.

* If you are unsure if your idea/code is suitable as a contrib, *ask the devs before putting any work into it*. This can also be a good idea in order to not duplicate efforts. This can also act as a check that your implementation idea is sound. We are, for example, unlikely to accept contribs that require large modifications of the game directory structure.
* If your code is intended *primarily* as an example or shows a concept/principle rather than a working system, it is probably not suitable for `contrib/`. You are instead welcome to use it as part of a [new tutorial][tutorials]!
* The code should ideally be contained within a single Python module. But if the contribution is large this may not be practical and it should instead be grouped in its own subdirectory (not as loose modules). 
* The contribution should preferably be isolated (only make use of core Evennia) so it can easily be dropped into use. If it does depend on other contribs or third-party modules, these must be clearly documented and part of the installation instructions.
* The code itself should follow Evennia's [Code style guidelines][codestyle].
* The code must be well documented as described in our [documentation style guide](https://github.com/evennia/evennia/blob/master/CODING_STYLE.md#doc-strings). Expect that your code will be read and should be possible to understand by others. Include comments as well as a header in all modules. If a single file, the header should include info about how to include the contrib in a game (installation instructions). If stored in a subdirectory, this info should go into a new `README.md` file within that directory.
* Within reason, your contribution should be designed as genre-agnostic as possible. Limit the amount of game-style-specific code. Assume your code will be applied to a very different game than you had in mind when creating it. 
* To make the licensing situation clear we assume all contributions are released with the same [license as Evennia](Licensing). If this is not possible for some reason, talk to us and we'll handle it on a case-by-case basis.
* Your contribution must be covered by [unit tests](Unit-Testing). Having unit tests will both help make your code more stable and make sure small changes does not break it without it being noticed, it will also help us test its functionality and merge it quicker. If your contribution is a single module, you can add your unit tests to `evennia/contribs/tests.py`. If your contribution is bigger and in its own sub-directory you could just put the tests in your own `tests.py` file (Evennia will find it automatically). 
* Merging of your code into Evennia is not guaranteed. Be ready to receive feedback and to be asked to make corrections or fix bugs. Furthermore, merging a contrib means the Evennia project takes on the responsibility of maintaining and supporting it. For various reasons this may be deemed to be beyond our manpower. However, if your code were to *not* be accepted for merger for some reason, we will instead add a link to your online repository so people can still find and use your work if they want. 

[ohloh]: http://www.ohloh.net/p/evennia
[patron]: https://www.patreon.com/griatch
[donate]: https://www.paypal.com/en/cgi-bin/webscr?cmd=_flow&SESSION=TWy_epDPSWqNr4UJCOtVWxl-pO1X1jbKiv_-UBBFWIuVDEZxC0M_2pM6ywO&dispatch=5885d80a13c0db1f8e263663d3faee8d66f31424b43e9a70645c907a6cbd8fb4
[forking]: https://github.com/evennia/evennia/wiki/Version-Control#wiki-forking-from-evennia
[pullrequest]: https://github.com/evennia/evennia/pulls
[issues]: https://github.com/evennia/evennia/issues
[patch]: https://secure.wikimedia.org/wikipedia/en/wiki/Patch_%28computing%29 
[codestyle]: https://github.com/evennia/evennia/blob/master/CODING_STYLE.md
[tutorials]: https://github.com/evennia/evennia/wiki/Tutorials
