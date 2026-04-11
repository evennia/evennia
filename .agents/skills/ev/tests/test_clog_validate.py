"""
Tests for ev-clog-validate.py — CHANGELOG.md validator.

TDD: tests written first, implementation follows.

Run with:
    python -m pytest .agents/skills/ev/tests/test_clog_validate.py -v
"""

import sys
import textwrap
from pathlib import Path

import pytest

# Make the skill directory importable so we can import the validator
SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_SECTION = textwrap.dedent("""\
    # Changelog

    ## Main branch

    - Feat: Something cool (Author)
    - [Fix][pull100]: Fix a bug (alice)
    - [Fix][issue200]: Fix another bug (bob)

    [pull100]: https://github.com/evennia/evennia/pull/100
    [issue200]: https://github.com/evennia/evennia/issues/200

    ## Evennia 1.0.0

    - [Fix][pull50]: Old fix (carol)

    [pull50]: https://github.com/evennia/evennia/pull/50
""")


# ---------------------------------------------------------------------------
# Mismatched URL tests
# ---------------------------------------------------------------------------


class TestMismatchedURLs:
    """Ref name number must match the number in the URL."""

    def test_clean(self, tmp_path):
        from clog_validate import validate_changelog
        f = tmp_path / "CHANGELOG.md"
        f.write_text(VALID_SECTION)
        errors = validate_changelog(f)
        mismatched = [e for e in errors if "mismatch" in e.lower()]
        assert mismatched == []

    def test_pull_url_number_mismatch(self, tmp_path):
        from clog_validate import validate_changelog
        f = tmp_path / "CHANGELOG.md"
        f.write_text(textwrap.dedent("""\
            # Changelog

            ## Main branch

            - [Fix][pull100]: Fix a bug (alice)

            [pull100]: https://github.com/evennia/evennia/pull/999
        """))
        errors = validate_changelog(f)
        mismatched = [e for e in errors if "mismatch" in e.lower()]
        assert len(mismatched) == 1
        assert "pull100" in mismatched[0]

    def test_issue_url_number_mismatch(self, tmp_path):
        from clog_validate import validate_changelog
        f = tmp_path / "CHANGELOG.md"
        f.write_text(textwrap.dedent("""\
            # Changelog

            ## Main branch

            - [Fix][issue3813]: Fix something (bob)

            [issue3813]: https://github.com/evennia/evennia/issues/3513
        """))
        errors = validate_changelog(f)
        mismatched = [e for e in errors if "mismatch" in e.lower()]
        assert len(mismatched) == 1
        assert "issue3813" in mismatched[0]

    def test_pull_ref_pointing_to_issues_url(self, tmp_path):
        from clog_validate import validate_changelog
        f = tmp_path / "CHANGELOG.md"
        f.write_text(textwrap.dedent("""\
            # Changelog

            ## Main branch

            - [Fix][pull100]: Fix (alice)

            [pull100]: https://github.com/evennia/evennia/issues/100
        """))
        errors = validate_changelog(f)
        mismatched = [e for e in errors if "mismatch" in e.lower()]
        assert len(mismatched) == 1


# ---------------------------------------------------------------------------
# Missing link ref tests
# ---------------------------------------------------------------------------


class TestMissingLinkRefs:
    """Entries that reference [pullNNN] or [issueNNN] must have a link ref."""

    def test_clean(self, tmp_path):
        from clog_validate import validate_changelog
        f = tmp_path / "CHANGELOG.md"
        f.write_text(VALID_SECTION)
        errors = validate_changelog(f)
        missing = [e for e in errors if "missing" in e.lower() and "link" in e.lower()]
        assert missing == []

    def test_entry_without_link_ref(self, tmp_path):
        from clog_validate import validate_changelog
        f = tmp_path / "CHANGELOG.md"
        f.write_text(textwrap.dedent("""\
            # Changelog

            ## Main branch

            - [Fix][pull100]: Fix a bug (alice)
        """))
        errors = validate_changelog(f)
        missing = [e for e in errors if "missing" in e.lower() and "link" in e.lower()]
        assert len(missing) == 1
        assert "pull100" in missing[0]

    def test_entries_without_refs_are_fine(self, tmp_path):
        """Entries like '- Fix: blah (Author)' have no ref and need no link."""
        from clog_validate import validate_changelog
        f = tmp_path / "CHANGELOG.md"
        f.write_text(textwrap.dedent("""\
            # Changelog

            ## Main branch

            - Fix: Something without a ref (Griatch)
            - Feat: Another thing (Griatch)
        """))
        errors = validate_changelog(f)
        missing = [e for e in errors if "missing" in e.lower() and "link" in e.lower()]
        assert missing == []


# ---------------------------------------------------------------------------
# Orphan link ref tests
# ---------------------------------------------------------------------------


class TestOrphanLinkRefs:
    """Link refs defined but never referenced in any entry."""

    def test_clean(self, tmp_path):
        from clog_validate import validate_changelog
        f = tmp_path / "CHANGELOG.md"
        f.write_text(VALID_SECTION)
        errors = validate_changelog(f)
        orphans = [e for e in errors if "orphan" in e.lower()]
        assert orphans == []

    def test_orphan_detected(self, tmp_path):
        from clog_validate import validate_changelog
        f = tmp_path / "CHANGELOG.md"
        f.write_text(textwrap.dedent("""\
            # Changelog

            ## Main branch

            - [Fix][pull100]: Fix a bug (alice)

            [pull100]: https://github.com/evennia/evennia/pull/100
            [pull999]: https://github.com/evennia/evennia/pull/999
        """))
        errors = validate_changelog(f)
        orphans = [e for e in errors if "orphan" in e.lower()]
        assert len(orphans) == 1
        assert "pull999" in orphans[0]


# ---------------------------------------------------------------------------
# Duplicate link ref tests
# ---------------------------------------------------------------------------


class TestDuplicateLinkRefs:
    """Same ref name defined more than once in a section."""

    def test_clean(self, tmp_path):
        from clog_validate import validate_changelog
        f = tmp_path / "CHANGELOG.md"
        f.write_text(VALID_SECTION)
        errors = validate_changelog(f)
        dupes = [e for e in errors if "duplicate" in e.lower()]
        assert dupes == []

    def test_duplicate_detected(self, tmp_path):
        from clog_validate import validate_changelog
        f = tmp_path / "CHANGELOG.md"
        f.write_text(textwrap.dedent("""\
            # Changelog

            ## Main branch

            - [Fix][pull100]: Fix a bug (alice)

            [pull100]: https://github.com/evennia/evennia/pull/100
            [pull100]: https://github.com/evennia/evennia/pull/100
        """))
        errors = validate_changelog(f)
        dupes = [e for e in errors if "duplicate" in e.lower()]
        assert len(dupes) == 1
        assert "pull100" in dupes[0]


# ---------------------------------------------------------------------------
# Multi-section tests
# ---------------------------------------------------------------------------


class TestMultipleSections:
    """Validation is per-section — refs in one section don't bleed into another."""

    def test_same_ref_in_different_sections_is_fine(self, tmp_path):
        from clog_validate import validate_changelog
        f = tmp_path / "CHANGELOG.md"
        f.write_text(textwrap.dedent("""\
            # Changelog

            ## Main branch

            - [Fix][pull100]: Fix v2 (alice)

            [pull100]: https://github.com/evennia/evennia/pull/100

            ## Evennia 1.0.0

            - [Fix][pull100]: Fix v1 (alice)

            [pull100]: https://github.com/evennia/evennia/pull/100
        """))
        errors = validate_changelog(f)
        assert errors == []

    def test_errors_report_section_name(self, tmp_path):
        from clog_validate import validate_changelog
        f = tmp_path / "CHANGELOG.md"
        f.write_text(textwrap.dedent("""\
            # Changelog

            ## Main branch

            - Feat: Clean section (Griatch)

            ## Evennia 1.0.0

            - [Fix][pull50]: Old fix (carol)
        """))
        errors = validate_changelog(f)
        missing = [e for e in errors if "missing" in e.lower() and "link" in e.lower()]
        assert len(missing) == 1
        assert "Evennia 1.0.0" in missing[0]


# ---------------------------------------------------------------------------
# Real CHANGELOG smoke test
# ---------------------------------------------------------------------------


class TestRealChangelog:
    """Run against the actual CHANGELOG.md — should pass cleanly."""

    def test_no_errors(self):
        from clog_validate import validate_changelog
        changelog = Path(__file__).resolve().parents[4] / "CHANGELOG.md"
        if not changelog.exists():
            pytest.skip("CHANGELOG.md not found at expected path")
        errors = validate_changelog(changelog)
        assert errors == [], f"Unexpected errors:\n" + "\n".join(errors)
