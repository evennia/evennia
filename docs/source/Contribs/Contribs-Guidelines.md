# Guidelines for Evennia contribs

Evennia has a [contrib](./Contribs-Overview.md) directory which contains optional, community-shared code organized by category. Anyone is welcome to contribute.

## What is suitable for a contrib?

- In general, you can contribute anything that you think may be useful to another developer. Unlike the 'core' Evennia, contribs can also be highly game-type-specific.
- Very small or incomplete snippets of code (e.g. meant to paste into some other code) are better shared as a post in the [Community Contribs & Snippets](https://github.com/evennia/evennia/discussions/2488) discussion forum category.
- If your code is intended *primarily* as an example or to show a concept/principle rather than a working system, consider if it may be better to instead [contribute to the documentation](../Contributing-Docs.md) by writing a new tutorial or howto.
- If possible, try to make your contribution as genre-agnostic as possible and assume
  your code will be applied to a very different game than you had in mind when creating it.
- The contribution should preferably work in isolation from other contribs (only make use of core Evennia) so it can easily be dropped into use. If it does depend on other contribs or third-party modules, these must be clearly documented and part of the installation instructions.
- If you are unsure about if your contrib idea is suitable or sound, *ask in discussions or chat before putting any work into it*. We are, for example, unlikely to accept contribs that require large modifications of the game directory structure.

## Layout of a contrib

- The contrib must be contained only within a single folder under one of the contrib categories below.  Ask if you are unsure which category fits best for your contrib.

|  |  | 
| --- | --- | 
| `base_systems/` | _Systems that are not necessarily tied to a specific in-game mechanic but which are useful for the game as a whole. Examples include login systems, new command syntaxes, and build helpers._ |
| `full_systems/` | _‘Complete’ game engines that can be used directly to start creating content without no further additions (unless you want to)._ |
| `game_systems/` | _In-game gameplay systems like crafting, mail, combat and more. Each system is meant to be adopted piecemeal and adopted for your game. This does not include roleplaying-specific systems, those are found in the `rpg` category._ |
| `grid/` | _Systems related to the game world’s topology and structure. Contribs related to rooms, exits and map building._ |
| `rpg/` | _Systems specifically related to roleplaying and rule implementation like character traits, dice rolling and emoting._ | 
| `tutorials/` | _Helper resources specifically meant to teach a development concept or to exemplify an Evennia system. Any extra resources tied to documentation tutorials are found here. Also the home of the Tutorial-World and Evadventure demo codes._ | 
| `tools/` | _Miscellaneous tools for manipulating text, security auditing, and more._|


- The folder (package) should be on the following form:

    ```
    evennia/
       contrib/ 
           category/    # rpg/, game_systems/ etc
               mycontribname/
                   __init__.py
                   README.md
                   module1.py
                   module2.py
                   ...
                   tests.py
    ```

    It's often a good idea to import useful resources in `__init__.py` to make it easier to import them.
- Your code should abide by the [Evennia Style Guide](../Coding/Evennia-Code-Style.md). Write it to be easy to read.
- Your contribution _must_ be covered by [unit tests](../Coding/Unit-Testing.md). Put your tests in a module `tests.py` under your contrib folder (as seen above) - Evennia will find them automatically.
-  The `README.md` file will be parsed and converted into a document linked from [the contrib overview page](./Contribs-Overview.md). It needs to be on the following form:

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

> The credit and first paragraph-summary will be automatically included on the Contrib overview page index for each contribution, so it needs to be just on this form.


## Submitting a contrib

```{sidebar} Not all PRs can be accepted
While most PRs get merged, this is not guaranteed: Merging a contrib means the Evennia project takes on the responsibility of maintaining and supporting the new code. For various reasons this may be deemed unfeasible. 

If your code were to *not* be accepted for some reason, we can still link it from our links page; it can also be posted in our discussion forum.
```
- A contrib must always be presented [as a pull request](../Coding/Version-Control.md#contributing-to-evennia) (PR).
- PRs are reviewed so don't be surprised (or disheartened) if you are asked to modify or change your code before it can be merged. Your code can end up going through several iterations before it is accepted.
- To make the licensing situation clear we assume all contributions are released with the same [license as Evennia](../Licensing.md). If this is not possible for some reason, talk to us and we'll handle it on a case-by-case basis. 
