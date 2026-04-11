---
name: ev
description: Evennia project management commands — list PRs, issues, and more.
---

# /ev — Evennia Project Skill

Route based on the first argument:

- `prs` → [List PRs awaiting maintainer review](#prs)
- `prs all` → [List all open PRs (including changes-requested)](#prs)
- `issues` → [List issues needing triage](#issues)
- `issues all` → [List all actionable open issues](#issues)
- `clog #NNN` → [Add changelog entry for a PR or issue](#clog)
- `clog <text>` → [Add freeform changelog entry](#clog)
- `clog validate` → [Validate CHANGELOG.md structure](#clog-validate)

If no argument or unrecognized subcommand, show available subcommands.

**Requires:** `gh` CLI. If not installed, ask the developer to install it
(https://cli.github.com/) — do not attempt workarounds.

---

## prs

**Usage:** `/ev prs [all]`

List open PRs on `evennia/evennia` that need maintainer attention.

- **`/ev prs`** — Only PRs awaiting review (excludes drafts, approved, and
  changes-requested PRs since those are waiting on the author). Sorted
  oldest-first with overlap annotations showing which PRs touch the same
  source files.
- **`/ev prs all`** — All open non-draft PRs that aren't yet approved,
  including changes-requested. Same ordering and overlap detection.

### Steps

1. Run the helper script from the skill directory, passing through any
   extra argument (`all` or empty):
   ```
   bash <skill_dir>/ev-prs.sh [all]
   ```
   where `<skill_dir>` is the directory containing this SKILL.md file.
2. Present the output directly to the user — it is already formatted as
   markdown with clickable URLs.

---

## issues

**Usage:** `/ev issues [all]`

List open issues on `evennia/evennia` that need maintainer attention. Sorted
oldest-first.

- **`/ev issues`** — Only issues labelled `needs-triage` (not yet reviewed).
- **`/ev issues all`** — All open issues except those waiting on someone else
  (excludes `more info needed`, `on hold`, `devel-implemented`).

### Steps

1. Run the helper script from the skill directory, passing through any
   extra argument (`all` or empty):
   ```
   bash <skill_dir>/ev-issues.sh [all]
   ```
   where `<skill_dir>` is the directory containing this SKILL.md file.
2. Present the output directly to the user — it is already formatted as
   markdown with clickable URLs.

---

## clog

**Usage:** `/ev clog #NNN` or `/ev clog <freeform text>`

Add a changelog entry to `CHANGELOG.md`.

### Routing

- If the argument is a number (with or without `#`), treat it as a **PR/issue
  number** and follow the [linked entry](#clog-linked) steps.
- Otherwise, treat the entire argument string as **freeform text** and follow
  the [freeform entry](#clog-freeform) steps.

### clog-linked

For PR/issue numbers.

1. Run the helper script to fetch metadata and generate the entry:
   ```
   bash <skill_dir>/ev-clog.sh <number>
   ```
   The script outputs **two lines**:
   - Line 1: the entry, e.g. `[Fix][pull3869]: Handle evennia -l & ... (jaborsh)`
   - Line 2: the link ref, e.g. `[pull3869]: https://github.com/...`
2. Show the generated entry to the user for approval. They may want to
   adjust the wording or category.
3. Read `CHANGELOG.md` and insert:
   - The **entry line** into the `## Main branch` section. Entries are
     ordered by category: `Feat` entries go at the top of the section,
     then `Fix`, then `Doc`/`Docs`. Insert the new entry after the last
     entry of the same category (or before the first entry of the next
     category if none exist yet). Always before the blank line that
     precedes the link references.
   - The **link reference** into the link-reference block at the bottom of
     the `## Main branch` section (before the next `## ` heading).
4. Show the user the final diff for confirmation.

### clog-freeform

For entries not tied to a specific PR or issue (local fixes, minor tweaks,
etc.). These produce unlinked entries with no link-reference line.

1. Parse the freeform text into a changelog entry. The text may already be
   a well-formed entry or just a rough description. Produce a line matching
   the format: `- <Cat>: <Description> (<Author>)` where:
   - **Cat** — guess from the text: `Feat`, `Fix`, `Doc`, or `Security`.
     Default to `Fix` if unclear.
   - **Description** — clean up the text: capitalize the first letter, trim
     trailing periods, keep it concise (one line preferred, wrap with
     two-space indent if truly needed).
   - **Author** — use the git user name (`git config user.name`). If the
     text already contains a parenthesised author, keep it.
2. Show the generated entry to the user for approval.
3. Read `CHANGELOG.md` and insert the entry line into the `## Main branch`
   section, ordered by category (same rules as linked entries). No link
   reference is needed.
4. Show the user the final diff for confirmation.

---

## clog-validate

**Usage:** `/ev clog validate`

Validate `CHANGELOG.md` structure. Checks each section for:

- **Mismatched URLs** — `[pull100]` must point to `/pull/100`, not a different number
  or `/issues/...`
- **Missing link refs** — entry references `[pull100]` but no `[pull100]: ...` defined
- **Orphan link refs** — `[pull100]: ...` defined but no entry uses `[pull100]`
- **Duplicate link refs** — same `[pull100]: ...` defined more than once

### Steps

1. Run the validator:
   ```
   python3 <skill_dir>/clog_validate.py CHANGELOG.md
   ```
2. Present the output directly to the user. If errors are found, offer to
   fix them.
