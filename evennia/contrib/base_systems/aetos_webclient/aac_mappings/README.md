# AAC symbol mappings

Concept-to-symbol mappings for the picture communication board (A7).

**These files contain no artwork.** Addendum A.63 permits bundling *concept
identifiers and mappings*; symbol imagery requires explicit licensing review.
So a mapping says "Aetos's `help` concept is Mulberry's `help_,_to` symbol", and
the image itself is obtained by whoever installs the pack.

## Why Aetos ships no symbols

Not because free sets do not exist — they do, and an earlier version of this
project said otherwise, wrongly. The real reasons differ per set:

| Set | Licence | Why it is not bundled |
| --- | --- | --- |
| [ARASAAC](https://arasaac.org) | CC BY-NC-SA | The **NonCommercial** clause. Aetos is BSD-3-Clause and games installing it may charge money. A player may install it; the contrib may not ship it. |
| [Mulberry](https://mulberrysymbols.org) | CC BY-SA 4.0 | Nothing legal — its own docs permit commercial use with attribution. **Coverage**: it is a vocabulary set, not a core board. |
| [Global Symbols](https://globalsymbols.com) / [Open Symbols](https://opensymbols.org) | mixed, per set | Aggregators. Each constituent set carries its own terms, so there is nothing uniform to verify. |

The Mulberry finding is the interesting one. It has 3,436 symbols whose largest
categories are country flags (254), country maps (188) and professions (164).
It has **no symbol for `yes`, `no`, `stop`, `please`, `thank you`, `sorry` or
`friend`** — the entire Common category, the words that must never be more than
one press away.

Bundling it would produce a board where the six most urgent words are the only
ones without a picture. That is worse than a board with no pictures: the
inconsistency is itself something to decode, and it is worst exactly where
hesitation costs most.

ARASAAC *does* cover that vocabulary, and is the one Aetos may not ship. That is
not a coincidence — a complete pictographic system is the kind of work whose
authors reasonably attach conditions.

## Building a pack

```bash
python scripts/build_symbol_pack.py mulberry --out mulberry-pack.json
```

Downloads the mapped symbols, inlines them as `data:` URIs, and writes a
self-contained pack file. Install it from the client: **Symbol packs** in the
command palette.

Self-contained matters beyond convenience. A pack of remote URLs tells whoever
hosts them, every time the board renders, that this browser is showing a
communication board — a disclosure about disability, made silently, to a third
party the player never chose to tell. The client reports which kind is
installed.

## Adding a mapping

A mapping file needs `set`, `name`, `license`, `attribution`, `source`,
`path_template` and `concepts`. Verify every entry against the set's own index
before adding it: a mapping that 404s renders as a missing image, and the player
finds out one word at a time, mid-conversation.

`scripts/build_symbol_pack.py --check` re-verifies every mapping against its
source without downloading anything.

## What still needs a person

Which set should be the default, whether the concept list should change to match
an available set, and — for sets that offer gendered variants like Mulberry's
`happy_man` / `happy_lady` — which to use, or whether offering either is right.

None of those are mine to settle (A.94). See `questions.md`.
