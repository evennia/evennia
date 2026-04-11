#!/usr/bin/env bash
# List open Evennia issues needing maintainer triage/review.
# Outputs markdown-formatted list with clickable URLs.
#
# Usage: ev-issues.sh [all]
#   (default)  Only issues labelled "needs-triage" (untriaged)
#   all        All open issues except those waiting on someone else
#              (excludes "more info needed", "on hold", "devel-implemented")
set -euo pipefail

REPO="evennia/evennia"
MODE="${1:-}"

if ! command -v gh &>/dev/null; then
    echo "ERROR: gh CLI not found. Install it: https://cli.github.com/"
    exit 1
fi

# Fetch open issues and open PRs (for cross-referencing)
issues_json=$(gh issue list -R "$REPO" --limit 100 --state open \
    --json number,title,author,labels,url,createdAt,comments)

prs_json=$(gh pr list -R "$REPO" --limit 50 --state open \
    --json number,title,body,url)

# Write PR data to a temp file so Python can read it without shell escaping issues
pr_tmp=$(mktemp)
trap 'rm -f "$pr_tmp"' EXIT
echo "$prs_json" > "$pr_tmp"

# Filter and format
echo "$issues_json" | python3 -c "
import json, sys, re

mode = '$MODE'
data = json.load(sys.stdin)

# Build issue-to-PR map from open PRs
with open('$pr_tmp') as f:
    prs = json.load(f)

issue_to_prs = {}
for pr in prs:
    text = (pr.get('title') or '') + ' ' + (pr.get('body') or '')
    for ref in re.findall(r'#(\d+)', text):
        issue_to_prs.setdefault(int(ref), []).append(pr)

# Labels that mean the issue is waiting on someone other than the maintainer
WAITING_LABELS = {'more info needed', 'on hold', 'devel-implemented'}

if mode == 'all':
    # All open issues except those blocked/waiting on others
    issues = [
        i for i in data
        if not WAITING_LABELS & {l['name'] for l in i['labels']}
    ]
else:
    # Default: only untriaged issues
    issues = [
        i for i in data
        if 'needs-triage' in {l['name'] for l in i['labels']}
    ]

if not issues:
    print('No open issues needing maintainer triage.')
    sys.exit(0)

# Sort oldest-first
issues.sort(key=lambda i: i['createdAt'])

for issue in issues:
    num = issue['number']
    title = issue['title']
    author = issue['author']['login']
    url = issue['url']
    labels = sorted(l['name'] for l in issue['labels'])
    label_str = ', '.join(labels)
    comments = len(issue.get('comments', []))
    comment_note = f' ({comments} comment{\"s\" if comments != 1 else \"\"})' if comments else ''
    linked = issue_to_prs.get(num, [])
    pr_note = ''
    if linked:
        pr_links = ', '.join(f'[#{p[\"number\"]}]({p[\"url\"]})' for p in linked)
        pr_note = f' — PR: {pr_links}'
    print(f'- **#{num}** — {title} (by @{author}) [{label_str}]{comment_note}{pr_note}')
    print(f'  {url}')
"
