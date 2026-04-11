"""
Validate CHANGELOG.md structure.

Checks per section:
  - Entries referencing [pullNNN] or [issueNNN] have a matching link ref
  - Link refs are not orphaned (defined but never referenced)
  - Link refs are not duplicated
  - Link ref URLs match their ref name (pullNNN -> /pull/NNN, issueNNN -> /issues/NNN)

Usage:
    python clog_validate.py <path-to-CHANGELOG.md>
"""

import re
import sys
from collections import Counter
from pathlib import Path

# Matches entry refs like [Fix][pull3869] — captures the ref name
ENTRY_REF_RE = re.compile(r"\]\[(pull\d+|issue\d+)\]")

# Matches link ref definitions like [pull3869]: https://...
LINK_DEF_RE = re.compile(r"^\[(pull\d+|issue\d+)\]:\s*(https?://\S+)")

# Extracts the number from a ref name
REF_NUM_RE = re.compile(r"(pull|issue)(\d+)")

# Extracts type and number from a GitHub URL
URL_RE = re.compile(r"github\.com/[^/]+/[^/]+/(pull|issues)/(\d+)")


def _parse_sections(text):
    """Split changelog into sections by ## headings.

    Returns list of (section_name, section_text) tuples.
    """
    sections = []
    current_name = None
    current_lines = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_name is not None:
                sections.append((current_name, "\n".join(current_lines)))
            current_name = line[3:].strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        sections.append((current_name, "\n".join(current_lines)))

    return sections


def _validate_section(section_name, section_text):
    """Validate a single changelog section. Returns list of error strings."""
    errors = []

    # Collect entry refs and link defs
    entry_refs = []
    link_defs = {}
    link_def_counts = Counter()

    for line in section_text.splitlines():
        # Entry refs
        for match in ENTRY_REF_RE.finditer(line):
            entry_refs.append(match.group(1))

        # Link definitions
        link_match = LINK_DEF_RE.match(line)
        if link_match:
            ref_name = link_match.group(1)
            url = link_match.group(2)
            link_def_counts[ref_name] += 1
            link_defs[ref_name] = url

    entry_ref_set = set(entry_refs)

    # Check for duplicate link refs
    for ref_name, count in link_def_counts.items():
        if count > 1:
            errors.append(
                f"[{section_name}] Duplicate link ref [{ref_name}] "
                f"(defined {count} times)"
            )

    # Check for missing link refs (entry references something not defined)
    for ref_name in entry_ref_set:
        if ref_name not in link_defs:
            errors.append(
                f"[{section_name}] Missing link ref [{ref_name}] "
                f"(referenced in entry but not defined)"
            )

    # Check for orphan link refs (defined but never referenced)
    for ref_name in link_defs:
        if ref_name not in entry_ref_set:
            errors.append(
                f"[{section_name}] Orphan link ref [{ref_name}] "
                f"(defined but not referenced by any entry)"
            )

    # Check URL mismatches
    for ref_name, url in link_defs.items():
        ref_match = REF_NUM_RE.match(ref_name)
        if not ref_match:
            continue
        ref_type = ref_match.group(1)  # "pull" or "issue"
        ref_num = ref_match.group(2)

        url_match = URL_RE.search(url)
        if not url_match:
            errors.append(
                f"[{section_name}] Link ref [{ref_name}] has "
                f"unrecognised URL format: {url}"
            )
            continue

        url_type = url_match.group(1)   # "pull" or "issues"
        url_num = url_match.group(2)

        # Check type: pull -> pull, issue -> issues
        expected_url_type = "pull" if ref_type == "pull" else "issues"
        if url_type != expected_url_type:
            errors.append(
                f"[{section_name}] URL type mismatch for [{ref_name}]: "
                f"ref is {ref_type} but URL points to /{url_type}/{url_num}"
            )
        elif url_num != ref_num:
            errors.append(
                f"[{section_name}] URL number mismatch for [{ref_name}]: "
                f"ref is #{ref_num} but URL points to #{url_num}"
            )

    return errors


def validate_changelog(path):
    """Validate a CHANGELOG.md file. Returns list of error strings."""
    text = Path(path).read_text()
    sections = _parse_sections(text)
    errors = []
    for section_name, section_text in sections:
        errors.extend(_validate_section(section_name, section_text))
    return errors


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python clog_validate.py <CHANGELOG.md>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"ERROR: {path} not found")
        sys.exit(1)

    errors = validate_changelog(path)
    if not errors:
        print("CHANGELOG.md is valid.")
        sys.exit(0)

    for error in errors:
        print(f"  {error}")
    print(f"\n{len(errors)} error(s) found.")
    sys.exit(1)
