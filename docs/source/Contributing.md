# How To Contribute And Get Help

If you cannot find what you are looking for in the documentation, here's what to do:

- If you need help, want to start a discussion or get some input on something
  you are working on, make a post to the [discussions forum][forum].
- If you want more direct discussions with developers and other users, drop
  into our very friendly [Discord channel][chat].
- If you think the documentation is not clear enough, create a [documentation issue][issues].
- If you have trouble with a missing feature or a problem you think is a bug,
  [request, or report it][issues].

## Community and Spreading the word

Being active and helpful in the [discssion forums][forum] or [chat][chat] is already a big help.

Consider writing about Evennia on your blog or in your favorite (relevant)
forum. Write a review somewhere (good or bad, we like feedback either way). Rate
it on listings. Talk about it to your friends ... that kind of thing.

## Help with Documentation

Evennia depends heavily on good documentation and we are always looking for
extra eyes and hands to improve it. Even small things such as fixing typos are a
great help!

- Easiest is to just [report documentation issues][issues] as you find them. If
  we don't know about them, we can't fix them!
- If you want to help editing the docs directly, [check here](./Contributing-Docs.md) on how to do it.
- If you have knowledge to share, how about writing a new [Tutorial](Howtos/Howtos-Overview.md)?

## Helping with code

If you find bugs, or have a feature-request, [make an issue][issues] for it. If
it's not in an issue, the issue will most likely be forgotten.

Even if you don't feel confident with tackling a bug or feature, just
correcting typos, adjusting formatting or simply *using* the thing and reporting
when stuff doesn't make sense helps us a lot.

- The code itself should follow Evennia's [Code style guidelines][codestyle] both
  for code and documentation. You should write code for that others can read an understand.
- Before merging, your code will be reviewed. Merging of your code into Evennia
  is not guaranteed. Be ready to receive feedback and to be asked to make
  corrections or fix bugs or any documentation issues and possibly tests (this
  is normal and nothing to worry about).

### Using a Forked reposity

The most elegant way to contribute code to Evennia is to use GitHub to create a
*fork* of the Evennia repository and make your changes to that. Refer to the
[Forking Evennia](Coding/Version-Control.md#forking-evennia) version control instructions for detailed instructions.

Once you have a fork set up, you can not only work on your own game in a
separate branch, you can also commit your fixes to Evennia itself.

- Make separate branches for all Evennia additions you do - don't edit your
  local `master` or `develop` branches directly. It will make your life a lot easier.
- If you have a change that you think is suitable for the main Evennia
  repository, issue a [Pull Request][pullrequest]. This will let Evennia devs know you have stuff to share.
- Bug fixes should generally be done against the `master` branch of Evennia,
  while new features/contribs should go into the `develop` branch. If you are
  unsure, just pick one and we'll figure it out.

### Contributing with Patches

To help with Evennia development it's strongly recommended to do so using a
forked repository as described above. But for small, well isolated fixes you are
also welcome to submit your suggested Evennia fixes/addendums as a
[patch][patch].

You can include your patch in an Issue or a Mailing list post. Please avoid
pasting the full patch text directly in your post though, best is to use a site
like [Pastebin](https://pastebin.com/) and just supply the link.

### Making an Evennia contrib

Evennia has a [contrib](Contribs/Contribs-Overview.md) directory which contains
user-shared code organized by category. You can contribute anything that you
think may be useful to another dev, also highly game-specific code. A contrib
must always be added via a forked repository.

#### Guidelines for making a contrib

- If you are unsure about if your contrib idea is suitable or sound, *ask in
  discussions or chat before putting any work into it*. We are, for example,
  unlikely to accept contribs that require large modifications of the game
  directory structure.
- If your code is intended *primarily* as an example or to show a
  concept/principle rather than a working system, you _can_ add to the
  `contribs/tutorials/` subfolder, but consider if it may be better to instead
  write a new tutorial doc page.
- The contribution should preferably work in isolation from other contribs (only
  make use of core Evennia) so it can easily be dropped into use. If it does
  depend on other contribs or third-party modules, these must be clearly
  documented and part of the installation instructions.
- The contrib must be contained within a separate folder under one of the
  contrib categories (`game_systems`, `rpg`, `utils` etc). Ask if you are
  unsure which category to put your contrib under.
- The folder (package) should be on the following form:

    ```
    mycontribname/
        __init__.py
        README.md
        module1.py
        module2.py
        ...
        tests.py
    ```

    It's often a good idea to import useful resources in `__init__.py` to make
    it easier to access them (this may vary though).

    The `README.md` will be parsed and converted into a document linked from
    [the contrib overview page](Contribs/Contribs-Overview.md). It should follow
    the following structure:

    ```markdown
    # MyContribName

    Contribution by <yourname>, <year>

    A paragraph (can be multi-line)
    summarizing the contrib (required)

    Optional other text

    ## Installation

    Detailed installation instructions for using the contrib (required)

    ## Usage

    ## Examples

    etc.

    ```

    The credit and first paragraph-summary will be used on the index page. Every
    contrib's readme must contain an installation instruction. See existing contribs
    for help.

- If possible, try to make contribution as genre-agnostic as possible and assume
  your code will be applied to a very different game than you had in mind when creating it.
- To make the licensing situation clear we assume all contributions are released
  with the same [license as Evennia](./Licensing.md). If this is not possible
for some reason, talk to us and we'll handle it on a case-by-case basis.
- Your contribution must be covered by [unit tests](Coding/Unit-Testing.md). Put
  your tests in a module `tests.py` under your contrib folder - Evennia will
  find them automatically.
- In addition to the normal review process, it's worth noting that merging a
  contrib means the Evennia project takes on the responsibility of maintaining
  and supporting it. For various reasons this may be deemed beyond our manpower.
- If your code were to *not* be accepted for some reason, you can ask us to
  instead link to your repo from our link page so people can find your code that
  way.

## Donations

Evennia is a free, open-source project and any monetary donations you want to
offer are _completely voluntary_. See it as a way of showing appreciation by
dropping a few coins in the cup.

- You can support Evennia as an [Evennia patreon][patron]. A patreon donates a
  (usually small) sum every month to show continued support.
- If a monthly donation is not your thing, you can also show your appreciation
  by doing a [one-time donation][donate] (this is a PayPal link but you don't need
  PayPal yourself to use it).


[patron]: https://www.patreon.com/griatch
[donate]: https://www.paypal.com/donate?token=zbU72YdRqPgsbpTw3M_4vR-5QJ7XvUhL9W6JlnPJw70M9LOqY1xD7xKGx0V1jLFSthY3xAztQpSsqW9n
[forking]: Coding/Version-Control#forking-evennia
[pullrequest]: https://github.com/evennia/evennia/pulls
[issues]: https://github.com/evennia/evennia/issues
[patch]: https://secure.wikimedia.org/wikipedia/en/wiki/Patch_%28computing%29
[codestyle]: https://github.com/evennia/evennia/blob/master/CODING_STYLE.md

[forum]:https://github.com/evennia/evennia/discussions
[issues]:https://github.com/evennia/evennia/issues/choose
[chat]: https://discord.com/invite/AJJpcRUhtF
[paypal]: https://www.paypal.com/se/cgi-bin/webscr?cmd=_flow&SESSION=Z-VlOvfGjYq2qvCDOUGpb6C8Due7skT0qOklQEy5EbaD1f0eyEQaYlmCc8O&dispatch=5885d80a13c0db1f8e263663d3faee8d64ad11bbf4d2a5a1a0d303a50933f9b2
[patreon]: https://www.patreon.com/griatch
[issues-bounties]:https://github.com/evennia/evennia/labels/bounty
[bountysource]: https://www.bountysource.com/teams/evennia
