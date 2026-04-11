"""
Tests for the /ev skill shell scripts (ev-prs.sh, ev-issues.sh).

Runs each script with a fake `gh` CLI that returns canned JSON,
then asserts on filtering, ordering, overlap detection, and PR
cross-referencing.

Run with:
    python -m pytest .agents/skills/ev/tests/ -v
"""

import json
import os
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_mock_gh(tmp_path, responses):
    """Create a mock ``gh`` script that returns canned JSON.

    Args:
        tmp_path: pytest tmp directory.
        responses: dict mapping a distinguishing keyword in the gh
            invocation to a JSON-serialisable object.  The mock iterates
            the dict and returns the first match whose key appears
            anywhere in the full command line.  Example::

                {"pr list": [...], "issue list": [...]}
    """
    # Build elif chain so one script can serve both pr and issue calls.
    branches = []
    for keyword, payload in responses.items():
        escaped = json.dumps(json.dumps(payload))  # shell-safe JSON
        branches.append(
            f'  *"{keyword}"*)\n    echo {escaped}\n    ;;'
        )
    body = "\n".join(branches)

    script = textwrap.dedent(f"""\
        #!/usr/bin/env bash
        args="$*"
        case "$args" in
        {body}
          *)
            echo "[]"
            ;;
        esac
    """)
    gh = tmp_path / "gh"
    gh.write_text(script)
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    return gh


def _run_script(script_name, tmp_path, responses, args=None):
    """Run a skill script with the mock gh on PATH and return stdout."""
    mock_gh = _write_mock_gh(tmp_path, responses)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}
    cmd = ["bash", str(SKILL_DIR / script_name)]
    if args:
        cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0 and "No open" not in result.stdout:
        raise RuntimeError(
            f"{script_name} failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result.stdout


# ---------------------------------------------------------------------------
# Fixtures — canned PR / issue data
# ---------------------------------------------------------------------------

def _pr(num, title, author="dev", decision="", is_draft=False, files=None,
        created="2026-01-01T00:00:00Z", body="", url=None):
    return {
        "number": num,
        "title": title,
        "author": {"login": author},
        "reviewDecision": decision,
        "isDraft": is_draft,
        "files": files or [],
        "createdAt": created,
        "body": body,
        "url": url or f"https://github.com/evennia/evennia/pull/{num}",
    }


def _issue(num, title, author="reporter", labels=None, comments=None,
           created="2026-01-01T00:00:00Z", url=None):
    return {
        "number": num,
        "title": title,
        "author": {"login": author},
        "labels": [{"name": l} for l in (labels or [])],
        "comments": comments or [],
        "createdAt": created,
        "url": url or f"https://github.com/evennia/evennia/issues/{num}",
    }


# ---------------------------------------------------------------------------
# ev-prs.sh tests
# ---------------------------------------------------------------------------


class TestPrsFiltering:
    """Default mode excludes drafts, approved, and changes-requested."""

    def test_excludes_drafts(self, tmp_path):
        prs = [
            _pr(1, "Draft PR", is_draft=True),
            _pr(2, "Real PR", created="2026-01-02T00:00:00Z"),
        ]
        out = _run_script("ev-prs.sh", tmp_path, {"pr list": prs})
        assert "#1" not in out
        assert "#2" in out

    def test_excludes_approved(self, tmp_path):
        prs = [
            _pr(1, "Approved PR", decision="APPROVED"),
            _pr(2, "Pending PR", created="2026-01-02T00:00:00Z"),
        ]
        out = _run_script("ev-prs.sh", tmp_path, {"pr list": prs})
        assert "#1" not in out
        assert "#2" in out

    def test_excludes_changes_requested_by_default(self, tmp_path):
        prs = [
            _pr(1, "Needs author work", decision="CHANGES_REQUESTED"),
            _pr(2, "Awaiting review", created="2026-01-02T00:00:00Z"),
        ]
        out = _run_script("ev-prs.sh", tmp_path, {"pr list": prs})
        assert "#1" not in out
        assert "#2" in out

    def test_all_mode_includes_changes_requested(self, tmp_path):
        prs = [
            _pr(1, "Needs author work", decision="CHANGES_REQUESTED"),
            _pr(2, "Awaiting review", created="2026-01-02T00:00:00Z"),
        ]
        out = _run_script("ev-prs.sh", tmp_path, {"pr list": prs}, args=["all"])
        assert "#1" in out
        assert "#2" in out

    def test_empty_list(self, tmp_path):
        out = _run_script("ev-prs.sh", tmp_path, {"pr list": []})
        assert "No open PRs" in out


class TestPrsOrdering:
    """PRs are sorted oldest-first by createdAt."""

    def test_oldest_first(self, tmp_path):
        prs = [
            _pr(3, "Newest", created="2026-03-01T00:00:00Z"),
            _pr(1, "Oldest", created="2026-01-01T00:00:00Z"),
            _pr(2, "Middle", created="2026-02-01T00:00:00Z"),
        ]
        out = _run_script("ev-prs.sh", tmp_path, {"pr list": prs})
        pos1 = out.index("#1")
        pos2 = out.index("#2")
        pos3 = out.index("#3")
        assert pos1 < pos2 < pos3


class TestPrsOverlaps:
    """PRs sharing non-test source files get overlap annotations."""

    def test_overlap_detected(self, tmp_path):
        shared_file = [{"path": "evennia/commands/cmdset.py",
                        "additions": 5, "deletions": 2, "changeType": "MODIFIED"}]
        prs = [
            _pr(1, "PR A", files=shared_file, created="2026-01-01T00:00:00Z"),
            _pr(2, "PR B", files=shared_file, created="2026-01-02T00:00:00Z"),
        ]
        out = _run_script("ev-prs.sh", tmp_path, {"pr list": prs})
        assert "overlaps #2" in out
        assert "overlaps #1" in out

    def test_no_overlap_on_different_files(self, tmp_path):
        prs = [
            _pr(1, "PR A",
                 files=[{"path": "evennia/a.py", "additions": 1,
                         "deletions": 0, "changeType": "MODIFIED"}],
                 created="2026-01-01T00:00:00Z"),
            _pr(2, "PR B",
                 files=[{"path": "evennia/b.py", "additions": 1,
                         "deletions": 0, "changeType": "MODIFIED"}],
                 created="2026-01-02T00:00:00Z"),
        ]
        out = _run_script("ev-prs.sh", tmp_path, {"pr list": prs})
        assert "overlaps" not in out

    def test_test_files_ignored_for_overlap(self, tmp_path):
        test_file = [{"path": "evennia/commands/tests.py",
                      "additions": 5, "deletions": 2, "changeType": "MODIFIED"}]
        prs = [
            _pr(1, "PR A", files=test_file, created="2026-01-01T00:00:00Z"),
            _pr(2, "PR B", files=test_file, created="2026-01-02T00:00:00Z"),
        ]
        out = _run_script("ev-prs.sh", tmp_path, {"pr list": prs})
        assert "overlaps" not in out


class TestPrsFormat:
    """Output lines have the expected markdown structure."""

    def test_line_format(self, tmp_path):
        prs = [_pr(42, "Fix a thing", author="alice")]
        out = _run_script("ev-prs.sh", tmp_path, {"pr list": prs})
        assert "- **#42** — Fix a thing (by @alice) [awaiting review]" in out
        assert "https://github.com/evennia/evennia/pull/42" in out

    def test_changes_requested_status_in_all_mode(self, tmp_path):
        prs = [_pr(7, "Needs work", decision="CHANGES_REQUESTED")]
        out = _run_script("ev-prs.sh", tmp_path, {"pr list": prs}, args=["all"])
        assert "[changes requested]" in out


# ---------------------------------------------------------------------------
# ev-issues.sh tests
# ---------------------------------------------------------------------------


class TestIssuesFiltering:
    """Default mode shows only needs-triage; all mode excludes waiting labels."""

    def test_default_shows_only_needs_triage(self, tmp_path):
        issues = [
            _issue(1, "Triaged bug", labels=["bug"]),
            _issue(2, "Untriaged bug", labels=["bug", "needs-triage"],
                   created="2026-01-02T00:00:00Z"),
        ]
        out = _run_script("ev-issues.sh", tmp_path,
                          {"issue list": issues, "pr list": []})
        assert "#1" not in out
        assert "#2" in out

    def test_all_mode_excludes_waiting_labels(self, tmp_path):
        issues = [
            _issue(1, "Active bug", labels=["bug"]),
            _issue(2, "Waiting for info", labels=["bug", "more info needed"],
                   created="2026-01-02T00:00:00Z"),
            _issue(3, "On hold", labels=["on hold"],
                   created="2026-01-03T00:00:00Z"),
            _issue(4, "Already done", labels=["devel-implemented"],
                   created="2026-01-04T00:00:00Z"),
        ]
        out = _run_script("ev-issues.sh", tmp_path,
                          {"issue list": issues, "pr list": []}, args=["all"])
        assert "#1" in out
        assert "#2" not in out
        assert "#3" not in out
        assert "#4" not in out

    def test_empty_list(self, tmp_path):
        out = _run_script("ev-issues.sh", tmp_path,
                          {"issue list": [], "pr list": []})
        assert "No open issues" in out


class TestIssuesOrdering:
    """Issues are sorted oldest-first."""

    def test_oldest_first(self, tmp_path):
        issues = [
            _issue(3, "Newest", labels=["needs-triage"],
                   created="2026-03-01T00:00:00Z"),
            _issue(1, "Oldest", labels=["needs-triage"],
                   created="2026-01-01T00:00:00Z"),
            _issue(2, "Middle", labels=["needs-triage"],
                   created="2026-02-01T00:00:00Z"),
        ]
        out = _run_script("ev-issues.sh", tmp_path,
                          {"issue list": issues, "pr list": []})
        pos1 = out.index("#1")
        pos2 = out.index("#2")
        pos3 = out.index("#3")
        assert pos1 < pos2 < pos3


class TestIssuesPRCrossRef:
    """Issues with linked PRs show the PR reference."""

    def test_linked_pr_shown(self, tmp_path):
        issues = [
            _issue(100, "Some bug", labels=["needs-triage"]),
        ]
        prs = [
            _pr(200, "Fix #100", body="Fixes #100"),
        ]
        out = _run_script("ev-issues.sh", tmp_path,
                          {"issue list": issues, "pr list": prs})
        assert "#100" in out
        assert "PR:" in out
        assert "#200" in out
        assert "https://github.com/evennia/evennia/pull/200" in out

    def test_no_pr_means_no_annotation(self, tmp_path):
        issues = [
            _issue(100, "Some bug", labels=["needs-triage"]),
        ]
        out = _run_script("ev-issues.sh", tmp_path,
                          {"issue list": issues, "pr list": []})
        assert "PR:" not in out

    def test_multiple_prs_for_one_issue(self, tmp_path):
        issues = [
            _issue(50, "Complex bug", labels=["needs-triage"]),
        ]
        prs = [
            _pr(60, "Attempt 1 for #50", body="See #50"),
            _pr(70, "Attempt 2 for #50", body="Fixes #50"),
        ]
        out = _run_script("ev-issues.sh", tmp_path,
                          {"issue list": issues, "pr list": prs})
        assert "#60" in out
        assert "#70" in out


class TestIssuesFormat:
    """Output lines have the expected markdown structure."""

    def test_line_format(self, tmp_path):
        issues = [
            _issue(42, "Exit bug", author="bob",
                   labels=["bug", "needs-triage"]),
        ]
        out = _run_script("ev-issues.sh", tmp_path,
                          {"issue list": issues, "pr list": []})
        assert "- **#42** — Exit bug (by @bob) [bug, needs-triage]" in out
        assert "https://github.com/evennia/evennia/issues/42" in out

    def test_comment_count_shown(self, tmp_path):
        issues = [
            _issue(42, "Chatty bug", labels=["needs-triage"],
                   comments=[{}, {}, {}]),
        ]
        out = _run_script("ev-issues.sh", tmp_path,
                          {"issue list": issues, "pr list": []})
        assert "(3 comments)" in out

    def test_single_comment_no_plural(self, tmp_path):
        issues = [
            _issue(42, "Quiet bug", labels=["needs-triage"],
                   comments=[{}]),
        ]
        out = _run_script("ev-issues.sh", tmp_path,
                          {"issue list": issues, "pr list": []})
        assert "(1 comment)" in out

    def test_zero_comments_no_annotation(self, tmp_path):
        issues = [
            _issue(42, "Silent bug", labels=["needs-triage"]),
        ]
        out = _run_script("ev-issues.sh", tmp_path,
                          {"issue list": issues, "pr list": []})
        assert "comment" not in out
