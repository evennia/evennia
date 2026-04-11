#!/usr/bin/env python3
"""
Agent context rot checker.

Validates that the agent knowledge base (AGENTS.md + .agents/docs/) stays lean,
cross-linked, and free of drift. Inspired by OpenAI's harness engineering approach:
AGENTS.md is a map (~100 lines), not a 1000-page manual. Detailed docs live in
.agents/docs/ and are only pulled in when needed.

Run from repo root:
    python .agents/tools/clean_rot.py

Exit code 0 = clean, 1 = warnings found.
"""

import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

# --- Thresholds ---

MAX_AGENTS_LINES = 40  # AGENTS.md is an index, not a manual
MAX_DOC_LINES = 120  # individual docs shouldn't bloat either
SIMILARITY_THRESHOLD = 0.6  # flag near-duplicate paragraphs between files
MIN_PARAGRAPH_LEN = 80  # ignore short lines for duplication checks


def _default_paths():
    """Return default paths derived from this script's location."""
    repo_root = Path(__file__).resolve().parents[2]
    return {
        "repo_root": repo_root,
        "agents_md": repo_root / "AGENTS.md",
        "docs_dir": repo_root / ".agents" / "docs",
        "src_dir": repo_root / "evennia",
    }


def warn(category, msg):
    """Print a categorized warning."""
    print(f"  [{category}] {msg}")


def check_line_budget(agents_md, docs_dir, repo_root, **_kw):
    """AGENTS.md is the table of contents — keep it short."""
    warnings = 0

    if agents_md.exists():
        lines = agents_md.read_text().splitlines()
        count = len(lines)
        if count > MAX_AGENTS_LINES:
            warn(
                "BLOAT",
                f"AGENTS.md is {count} lines (budget: {MAX_AGENTS_LINES}). "
                f"Move detail into .agents/docs/ and keep AGENTS.md as an index.",
            )
            warnings += 1
    else:
        warn("MISSING", "AGENTS.md not found.")
        warnings += 1

    if docs_dir.exists():
        for doc in sorted(docs_dir.glob("*.md")):
            lines = doc.read_text().splitlines()
            count = len(lines)
            if count > MAX_DOC_LINES:
                warn(
                    "BLOAT",
                    f"{doc.relative_to(repo_root)} is {count} lines "
                    f"(budget: {MAX_DOC_LINES}). Consider splitting.",
                )
                warnings += 1

    return warnings


def check_broken_links(agents_md, docs_dir, repo_root, **_kw):
    """Verify all markdown links in AGENTS.md and .agents/docs/ point to files that exist."""
    warnings = 0
    if not agents_md.exists():
        return 0

    text = agents_md.read_text()
    # Match markdown links: [text](path) — skip http(s) URLs
    for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
        label, target = match.group(1), match.group(2)
        if target.startswith(("http://", "https://", "#")):
            continue
        resolved = repo_root / target
        if not resolved.exists():
            warn("BROKEN_LINK", f"AGENTS.md links to '{target}' ({label}) — file not found.")
            warnings += 1

    # Also check links inside .agents/docs/
    if docs_dir.exists():
        for doc in docs_dir.glob("*.md"):
            doc_text = doc.read_text()
            for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", doc_text):
                label, target = match.group(1), match.group(2)
                if target.startswith(("http://", "https://", "#")):
                    continue
                resolved = doc.parent / target
                if not resolved.exists():
                    rel = doc.relative_to(repo_root)
                    warn("BROKEN_LINK", f"{rel} links to '{target}' ({label}) — file not found.")
                    warnings += 1

    return warnings


def check_orphan_docs(agents_md, docs_dir, repo_root, **_kw):
    """Every file in .agents/docs/ should be referenced from AGENTS.md."""
    warnings = 0
    if not docs_dir.exists() or not agents_md.exists():
        return 0

    agents_text = agents_md.read_text()
    for doc in sorted(docs_dir.glob("*.md")):
        rel_path = str(doc.relative_to(repo_root))
        # Check both with and without leading ./
        if rel_path not in agents_text and f"./{rel_path}" not in agents_text:
            warn(
                "ORPHAN",
                f"{rel_path} is not referenced from AGENTS.md — "
                f"agents won't discover it via progressive disclosure.",
            )
            warnings += 1

    return warnings


def _extract_paragraphs(text):
    """Split text into non-trivial paragraphs for duplication checking."""
    paragraphs = []
    current = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                para = " ".join(current)
                if len(para) >= MIN_PARAGRAPH_LEN:
                    paragraphs.append(para)
                current = []
        else:
            # Skip code blocks and headings
            if not stripped.startswith(("```", "#", "- ", "| ")):
                current.append(stripped)
    if current:
        para = " ".join(current)
        if len(para) >= MIN_PARAGRAPH_LEN:
            paragraphs.append(para)
    return paragraphs


def check_duplication(agents_md, docs_dir, repo_root, **_kw):
    """Flag near-duplicate content between AGENTS.md and .agents/docs/ files.

    Duplication means AGENTS.md is inlining detail instead of pointing to it.
    """
    warnings = 0
    if not agents_md.exists() or not docs_dir.exists():
        return 0

    agents_paragraphs = _extract_paragraphs(agents_md.read_text())

    for doc in sorted(docs_dir.glob("*.md")):
        doc_paragraphs = _extract_paragraphs(doc.read_text())
        rel = doc.relative_to(repo_root)

        for ap in agents_paragraphs:
            for dp in doc_paragraphs:
                ratio = SequenceMatcher(None, ap, dp).ratio()
                if ratio >= SIMILARITY_THRESHOLD:
                    snippet = ap[:80] + "..." if len(ap) > 80 else ap
                    warn(
                        "DUPLICATION",
                        f"AGENTS.md duplicates content from {rel} "
                        f"({ratio:.0%} similar): \"{snippet}\"",
                    )
                    warnings += 1

    return warnings


def check_stale_references(agents_md, docs_dir, repo_root, src_dir, **_kw):
    """Check that source paths and Python module paths mentioned in docs still exist.

    Only flags references that look like intentional source tree paths (must contain
    a slash for file paths, or start with 'evennia.' for dotted module paths). Bare
    filenames, CLI tools, branch names, and Python identifiers are ignored.
    """
    warnings = 0

    all_docs = []
    if agents_md.exists():
        all_docs.append(agents_md)
    if docs_dir.exists():
        all_docs.extend(docs_dir.glob("*.md"))

    for doc in all_docs:
        text = doc.read_text()
        rel = doc.relative_to(repo_root)

        # Check backtick-quoted paths that contain a slash (real source paths).
        # e.g. `commands/default/`, `typeclasses/attributes.py`, `server/conf/settings.py`
        # Skips bare filenames like `cmdhandler.py` and tools like `uv`.
        for match in re.finditer(
            r"`((?:evennia/)?[a-z_]+/[a-z_/]*(?:\.py)?/?)`", text
        ):
            path_ref = match.group(1)
            # Search broadly: repo root, src dir, src/contrib,
            # game_template (for game-dir paths like server/conf/settings.py)
            candidates = [
                src_dir / path_ref,
                repo_root / path_ref,
                src_dir / "contrib" / path_ref,
                src_dir / "game_template" / path_ref,
            ]
            if path_ref.startswith("evennia/"):
                candidates.append(repo_root / path_ref)
            if not any(c.exists() for c in candidates):
                warn("STALE_REF", f"{rel} references `{path_ref}` — path not found in source.")
                warnings += 1

        # Check backtick-quoted Python dotted paths like `evennia.objects.tests`
        for match in re.finditer(r"`(evennia\.[a-z_.]+)`", text):
            dotted = match.group(1)
            parts = dotted.split(".")
            as_file = repo_root / Path(*parts).with_suffix(".py")
            as_dir = repo_root / Path(*parts)
            as_init = as_dir / "__init__.py"
            if not (as_file.exists() or as_dir.exists() or as_init.exists()):
                warn("STALE_REF", f"{rel} references `{dotted}` — module not found.")
                warnings += 1

    return warnings


def check_index_density(agents_md, **_kw):
    """AGENTS.md should be mostly pointers, not prose. Check the ratio of
    link/reference lines vs content lines."""
    warnings = 0
    if not agents_md.exists():
        return 0

    text = agents_md.read_text()
    lines = text.splitlines()
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return 0

    # Count lines that are structural: headings, links, bullets, code blocks, blank
    structural_pattern = re.compile(
        r"^\s*$|"  # blank
        r"^#+\s|"  # heading
        r"^```|"  # code fence
        r".*\[.*\]\(.*\)|"  # contains a link
        r"^\s*[-*]\s|"  # bullet point
        r"^@"  # directive
    )
    in_code_block = False
    structural = 0
    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            structural += 1
        elif in_code_block:
            structural += 1  # code block contents are structural
        elif structural_pattern.match(line):
            structural += 1
    prose = len(lines) - structural

    # If more than 50% of AGENTS.md is prose, it's becoming a manual
    if non_empty and prose / len(non_empty) > 0.50:
        warn(
            "DENSITY",
            f"AGENTS.md is {prose / len(non_empty):.0%} prose — "
            f"keep it as an index with pointers. Move prose to .agents/docs/.",
        )
        warnings += 1

    return warnings


ALL_CHECKS = [
    ("Line budgets", check_line_budget),
    ("Broken links", check_broken_links),
    ("Orphan docs", check_orphan_docs),
    ("Duplication", check_duplication),
    ("Stale references", check_stale_references),
    ("Index density", check_index_density),
]


def main():
    paths = _default_paths()
    print(f"Agent context rot check: {paths['repo_root']}\n")

    total = 0
    for name, fn in ALL_CHECKS:
        print(f"Checking {name}...")
        count = fn(**paths)
        total += count
        if count == 0:
            print("  OK")

    print()
    if total == 0:
        print("All clean — agent context is lean.")
        return 0
    else:
        print(f"{total} warning(s) found — review above to keep context rot-free.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
