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

**Usage:** `/ev clog #NNN`

Add a changelog entry to `CHANGELOG.md` for a merged PR or resolved issue,
crediting the contributor.

### Steps

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
   - The **entry line** into the `## Main branch` section, after the last
     existing entry line (before the blank line that precedes the link
     references).
   - The **link reference** into the link-reference block at the bottom of
     the `## Main branch` section (before the next `## ` heading).
4. Show the user the final diff for confirmation.
