# GitHub Issues & PRs

Use the `gh` CLI to interact with the Evennia repository on GitHub
(`-R evennia/evennia`).
If `gh` is not installed, ask the developer to install it — do not attempt
workarounds.

## Listing

```bash
gh issue list -R evennia/evennia                    # open issues
gh pr list -R evennia/evennia                       # open PRs
gh issue list -R evennia/evennia --search "keyword"  # search issues
gh pr list -R evennia/evennia --search "keyword"     # search PRs
```

## Viewing Details

```bash
gh issue view <number> -R evennia/evennia
gh pr view <number> -R evennia/evennia
gh pr diff <number> -R evennia/evennia               # PR diff
gh api repos/evennia/evennia/pulls/<number>/comments  # PR review comments
```

## Output Formatting

When presenting issues or PRs to the user, always include a clickable URL:

```
#3850 — Fix EvMenu node persistence (https://github.com/evennia/evennia/issues/3850)
```

Use the `evennia/evennia#<number>` shorthand where markdown rendering supports it.
