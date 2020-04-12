```python
class Documentation:
    RATING = "Excellent"
```
# Becoming a Contributor

Evennia is an open-source, community-developed system for building games. That means your contributions are critical to growing the game's features.

Anyone can be a contributor, even with only a couple of months of experience under their belts! Here are some of the ways you can help:

- Spreading the word!
- Reproducing issues noted by other players
- Implementing new features for your own game, then sharing them as contribs
- Patching issues listed on GitHub
- Improving documentation
- Expanding Evennia's functionality by making it more agnostic
- Sending cash to motivate our maintainer(s)

#### Spreading the Word

Even if you are not keen on working on the server code yourself, just spreading the word is a big help - it will help attract more people which leads to more feedback, motivation and interest. Consider writing about Evennia on your blog or in your favorite (relevant) forum. Write a review somewhere (good or bad, we like feedback either way). Rate it on places like [ohloh][ohloh]. Talk about it to your friends, get a JörMUDgandr tattoo, that kind of thing.

#### Reproducing Issues

The first step in fixing an issue is seeing if it affects multiple players. The [Issues][issues] tab on GitHub is a list of all of our open bug reports. Typically, a bug report _should_ contain steps to reproduce the bug. If you follow these steps, did you reproduce the bug the original poster mentioned? 

If so, write a comment and let us know you were able to reproduce it! This helps confirm that it's not a problem with the bug reporter's own game, installation environment, or another one-off issue that we can't actually fix.

If you can't reproduce it - even better! Write and let us know that. It helps to narrow down the places we look, and it will hopefully encourage the poster to review his or her issue and dig a little deeper into fixing it.

#### Sharing contribs

The `contribs` directory is where we share user-contributed code that might be a little too game-specific for inclusion in the core. This doesn't mean the code is any worse than what's in the core, it might just be that it's only a useful functionality in a particular type of game.

Even if there's nobody building a game exactly like you are today, contribs will help the next developers who join the Evennia project get a headstart. Contribs range across the board from puzzle rooms to clothing, from combat systems to NPC dialog.

* If you are unsure if your idea/code is suitable as a contrib, *ask someone before putting too much work into it*. The devs don't bite, and they're available all the time in IRC and on GitHub! They can help you shape your idea and implementation. 
* If your code is intended *primarily* as an example or shows a concept/principle rather than a working system, it is probably not suitable for `contrib/`. You are instead welcome to use it as part of a [new tutorial][tutorials]!
* The code should ideally be contained within a single Python module. But if the contribution is large this may not be practical and it should instead be grouped in its own subdirectory (not as loose modules). 
* The contribution should preferably be isolated (only make use of core Evennia) so it can easily be dropped into use. If it does depend on other contribs or third-party modules, these must be clearly documented and part of the installation instructions.
* Within reason, your contribution should be designed as genre-agnostic as possible. Limit the amount of game-style-specific code. Assume your code will be applied to a very different game than you had in mind when creating it. 
* The code should follow Evennia's [Code style guidelines][codestyle].
* The code should be documented according to Evennia's [Documentation guidelines](../documentation/DocumentationStyleGuide)
* The code should adhere to Evennia's [License](../licensing/FAQ)
* The code should be covered by [unit tests](../../tutorials_and_examples/python/Unit-Testing)

|_Protip_|Contributing to Evennia|
|---|---|
|![JörMUDgandr][logo] | _JörMUDgandr says, "Merging of your code into Evennia is not guaranteed. Be ready to receive feedback and to be asked to make corrections or fix bugs - all in the spirit of making you a better developer!"_ |

#### Patching Issues on GitHub

The most elegant way to contribute code to Evennia is to use GitHub to create a *fork* of the Evennia repository and make your changes to that. Refer to the [Forking Evennia][forking] version control instructions for detailed instructions. 

Once you have a fork set up, you can not only work on your own game in a separate branch, you can also commit your fixes to Evennia itself. Make separate branches for all Evennia additions you do - don't edit your local `master` or `develop` branches directly. It will make your life a lot easier. If you have a change that you think is suitable for the main Evennia repository, you issue a [Pull Request][pullrequest]. This will let Evennia devs know you have stuff to share. Bug fixes should generally be done against the `master` branch of Evennia, while new features/contribs should go into the `develop` branch. If you are unsure, just pick one and we'll figure it out.
 
To help with Evennia development it's recommended to do so using a fork repository as described above. But for small, well isolated fixes you are also welcome to submit your suggested Evennia fixes/addendums as a [patch][patch].

You can include your patch in an Issue or a Mailing list post. Please avoid pasting the full patch text directly in your post though, best is to use a site like [Pastebin](http://pastebin.com/) and just supply the link. 

#### Improving Documentation
Evennia depends heavily on good documentation and we are always looking for extra eyes and hands to improve it. Even small things such as fixing typos are a great help!

The documentation is a wiki and as long as you have a GitHub account you can edit it. It can be a good idea to discuss in the chat or forums if you want to add new pages/tutorials. Otherwise, it goes a long way just pointing out wiki errors so we can fix them (in an Issue or just over chat/forum).

#### Adding Major Features
Evennia's core philosophy is to be genre-agnostic. As much as possible, we want it to be possible for users who are not satisfied with the default options to change them, modify them, or remove them entirely. After all - it's your game, you do what you want.

Even still, there are a lot of features that are just 'the Evennia way.' If you have a big idea for how you can contribute in a major capacity to making the source easier to grok, better to use, or more capable of handling a diverse set of use cases, that's great! Come join the illustrious few: _the authors_. 

#### Donating
The laziest way to support Evennia is to become an [Evennia patron][patron]. Evennia is a free, open-source project and any monetary donations you want to offer are completely voluntary. See it as a way of announcing that you appreciate the work done - a tip of the hat! A patron donates a (usually small) sum every month to show continued support.  If this is not your thing, you can also show your appreciation via a [one-time donation][donate].

[ohloh]: http://www.ohloh.net/p/evennia
[patron]: https://www.patreon.com/griatch
[donate]: https://www.paypal.com/en/cgi-bin/webscr?cmd=_flow&SESSION=TWy_epDPSWqNr4UJCOtVWxl-pO1X1jbKiv_-UBBFWIuVDEZxC0M_2pM6ywO&dispatch=5885d80a13c0db1f8e263663d3faee8d66f31424b43e9a70645c907a6cbd8fb4
[forking]: https://github.com/evennia/evennia/wiki/Version-Control#wiki-forking-from-evennia
[pullrequest]: https://github.com/evennia/evennia/pulls
[issues]: https://github.com/evennia/evennia/issues
[patch]: https://secure.wikimedia.org/wikipedia/en/wiki/Patch_%28computing%29 
[codestyle]: https://github.com/evennia/evennia/blob/master/CODING_STYLE.md
[tutorials]: https://github.com/evennia/evennia/wiki/Tutorials
[logo]: https://raw.githubusercontent.com/evennia/evennia/master/evennia/web/website/static/website/images/evennia_logo.png


