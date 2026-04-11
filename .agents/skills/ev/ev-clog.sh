#!/usr/bin/env bash
# Fetch PR or issue metadata and output a changelog entry + link ref.
# Outputs two lines: the entry line and the markdown link reference.
#
# Usage: ev-clog.sh <number>
#   number   A PR or issue number (with or without leading #)
set -euo pipefail

REPO="evennia/evennia"
NUM="${1#\#}"  # strip leading # if present

if ! command -v gh &>/dev/null; then
    echo "ERROR: gh CLI not found. Install it: https://cli.github.com/"
    exit 1
fi

if [[ -z "$NUM" ]]; then
    echo "ERROR: provide a PR or issue number, e.g.: ev-clog.sh 3869"
    exit 1
fi

# Try PR first, fall back to issue
kind=""
json=""

pr_json=$(gh pr view "$NUM" -R "$REPO" --json number,title,author,url,state 2>/dev/null || true)
if [[ -n "$pr_json" && "$pr_json" != "null" ]]; then
    kind="pull"
    json="$pr_json"
else
    issue_json=$(gh issue view "$NUM" -R "$REPO" --json number,title,author,url,labels,state 2>/dev/null || true)
    if [[ -n "$issue_json" && "$issue_json" != "null" ]]; then
        kind="issue"
        json="$issue_json"
    fi
fi

if [[ -z "$kind" ]]; then
    echo "ERROR: #$NUM not found as a PR or issue on $REPO"
    exit 1
fi

echo "$json" | python3 -c "
import json, sys, re

kind = '$kind'
data = json.load(sys.stdin)

num = data['number']
title = data['title']
author = data['author']['login']
url = data['url']

# Strip common title prefixes from issues
clean = re.sub(
    r'^\s*\[(BUG|Feature Request|Documentation|Security)\]\s*',
    '', title, flags=re.IGNORECASE
).strip()
# Strip common PR title prefixes
clean = re.sub(
    r'^(fix|feat|docs?|nit|chore|refactor)[:/]\s*',
    '', clean, flags=re.IGNORECASE
).strip()
# Capitalise first letter
if clean:
    clean = clean[0].upper() + clean[1:]

# Guess category from title / labels
title_lower = title.lower()
labels = [l['name'] for l in data.get('labels', [])]
label_names = {l.lower() for l in labels}

if 'documentation' in label_names or title_lower.startswith(('[documentation]', 'docs:', 'doc:')):
    cat = 'Doc'
elif 'security' in label_names or 'security' in title_lower:
    cat = 'Security'
elif 'feature-request' in label_names or title_lower.startswith(('[feature request]', 'feat:', 'feat(')):
    cat = 'Feat'
else:
    cat = 'Fix'

ref = f'{kind}{num}'
entry = f'- [{cat}][{ref}]: {clean} ({author})'
link = f'[{ref}]: {url}'

# Warn if not yet merged/closed
state = data.get('state', '').upper()
if kind == 'pull' and state == 'CLOSED':
    print(f'WARNING: PR #{num} was closed without merging. Wrong number?')
elif kind == 'pull' and state != 'MERGED':
    print(f'WARNING: PR #{num} is not yet merged (state: {state}). Wrong number?')
elif kind == 'issue' and state != 'CLOSED':
    print(f'WARNING: Issue #{num} is not closed (state: {state}). Wrong number?')

print(entry)
print(link)
"
