#!/usr/bin/env bash
# List open Evennia PRs pending maintainer action.
# Outputs markdown-formatted list with clickable URLs.
#
# Usage: ev-prs.sh [all]
#   (default)  Only PRs awaiting review (excludes changes-requested / approved)
#   all        All open non-draft PRs that aren't approved
set -euo pipefail

REPO="evennia/evennia"
MODE="${1:-}"

if ! command -v gh &>/dev/null; then
    echo "ERROR: gh CLI not found. Install it: https://cli.github.com/"
    exit 1
fi

# Fetch open, non-draft PRs with review status and changed files
json=$(gh pr list -R "$REPO" --limit 50 --state open \
    --json number,title,author,reviewDecision,isDraft,url,createdAt,files,reviews)

# Filter, detect dependencies, and format
echo "$json" | python3 -c "
import json, subprocess, sys
from collections import defaultdict

mode = '$MODE'
repo = '$REPO'
data = json.load(sys.stdin)

STATUS_MAP = {
    '': 'awaiting review',
    'REVIEW_REQUIRED': 'awaiting review',
    'APPROVED': 'approved',
    'CHANGES_REQUESTED': 'changes requested',
}

def last_changes_requested_time(pr):
    \"\"\"Return the timestamp of the latest CHANGES_REQUESTED review, or None.\"\"\"
    last_cr = None
    for r in pr.get('reviews', []):
        if r.get('state') == 'CHANGES_REQUESTED':
            ts = r.get('submittedAt', '')
            if ts and (last_cr is None or ts > last_cr):
                last_cr = ts
    return last_cr

def get_last_commit_time(pr_number):
    \"\"\"Fetch the latest commit timestamp for a PR via gh.\"\"\"
    try:
        result = subprocess.run(
            ['gh', 'pr', 'view', str(pr_number), '-R', repo,
             '--json', 'commits', '--jq', '.commits[-1].committedDate'],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip()
    except Exception:
        return ''

def has_new_commits_after_review(pr):
    \"\"\"Check if the PR has commits pushed after the latest changes-requested review.\"\"\"
    last_cr = last_changes_requested_time(pr)
    if not last_cr:
        return False
    last_commit = get_last_commit_time(pr['number'])
    return bool(last_commit) and last_commit > last_cr

# Start with non-draft, not-approved PRs
pending = [
    pr for pr in data
    if not pr['isDraft'] and pr['reviewDecision'] != 'APPROVED'
]

# Default mode: only PRs actually awaiting maintainer review.
# Include changes-requested PRs if the author pushed new commits after review.
if mode != 'all':
    pending = [
        pr for pr in pending
        if pr['reviewDecision'] != 'CHANGES_REQUESTED'
        or has_new_commits_after_review(pr)
    ]

if not pending:
    print('No open PRs pending maintainer action.')
    sys.exit(0)

# Sort oldest-first
pending.sort(key=lambda pr: pr['createdAt'])

# Detect file overlaps between PRs (ignore test files).
file_to_prs = defaultdict(set)
pr_files = {}
for pr in pending:
    paths = {
        f['path'] for f in pr.get('files', [])
        if not f['path'].split('/')[-1].startswith('test')
    }
    pr_files[pr['number']] = paths
    for p in paths:
        file_to_prs[p].add(pr['number'])

# For each PR, find which other PRs directly share source files
def get_overlaps(num):
    others = set()
    for p in pr_files.get(num, []):
        others |= file_to_prs[p]
    others.discard(num)
    return sorted(others)

for pr in pending:
    num = pr['number']
    title = pr['title']
    author = pr['author']['login']
    decision = pr['reviewDecision']
    url = pr['url']
    overlaps = get_overlaps(num)

    # Determine display status
    if decision == 'CHANGES_REQUESTED' and has_new_commits_after_review(pr):
        status = 'updated since review'
    else:
        status = STATUS_MAP.get(decision, decision)

    overlap_note = ''
    if overlaps:
        refs = ', '.join(f'#{n}' for n in overlaps)
        overlap_note = f' — overlaps {refs}'
    print(f'- **#{num}** — {title} (by @{author}) [{status}]{overlap_note}')
    print(f'  {url}')
"
