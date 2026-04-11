"""
Tests for .agents/tools/clean_rot.py

Run with:
    python -m pytest .agents/tools/tests/ -v
"""

import sys
import textwrap
from pathlib import Path

import pytest

# Make the tools package importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clean_rot import (
    _extract_paragraphs,
    check_broken_links,
    check_duplication,
    check_index_density,
    check_line_budget,
    check_orphan_docs,
    check_stale_references,
)


@pytest.fixture
def repo(tmp_path):
    """Scaffold a minimal fake repo for testing."""
    agents_md = tmp_path / "AGENTS.md"
    docs_dir = tmp_path / ".agents" / "docs"
    src_dir = tmp_path / "evennia"
    docs_dir.mkdir(parents=True)
    src_dir.mkdir()
    return {
        "repo_root": tmp_path,
        "agents_md": agents_md,
        "docs_dir": docs_dir,
        "src_dir": src_dir,
    }


# ---- check_line_budget ----


class TestLineBudget:
    def test_clean(self, repo):
        repo["agents_md"].write_text("# Index\n\n- [Foo](foo.md)\n")
        assert check_line_budget(**repo) == 0

    def test_missing_agents_md(self, repo):
        assert check_line_budget(**repo) == 1

    def test_agents_md_over_budget(self, repo):
        repo["agents_md"].write_text("\n".join(f"line {i}" for i in range(50)))
        assert check_line_budget(**repo) == 1

    def test_agents_md_at_budget(self, repo):
        repo["agents_md"].write_text("\n".join(f"line {i}" for i in range(40)))
        assert check_line_budget(**repo) == 0

    def test_doc_over_budget(self, repo):
        repo["agents_md"].write_text("# Index\n")
        (repo["docs_dir"] / "big.md").write_text("\n".join(f"line {i}" for i in range(150)))
        assert check_line_budget(**repo) == 1

    def test_doc_under_budget(self, repo):
        repo["agents_md"].write_text("# Index\n")
        (repo["docs_dir"] / "small.md").write_text("# Small doc\n\nSome content.\n")
        assert check_line_budget(**repo) == 0


# ---- check_broken_links ----


class TestBrokenLinks:
    def test_clean(self, repo):
        (repo["docs_dir"] / "arch.md").write_text("# Architecture\n")
        repo["agents_md"].write_text("See [Arch](.agents/docs/arch.md)\n")
        assert check_broken_links(**repo) == 0

    def test_broken_link_in_agents(self, repo):
        repo["agents_md"].write_text("See [Missing](does/not/exist.md)\n")
        assert check_broken_links(**repo) == 1

    def test_http_links_skipped(self, repo):
        repo["agents_md"].write_text("See [Docs](https://example.com)\n")
        assert check_broken_links(**repo) == 0

    def test_anchor_links_skipped(self, repo):
        repo["agents_md"].write_text("See [Section](#section)\n")
        assert check_broken_links(**repo) == 0

    def test_broken_link_in_doc(self, repo):
        repo["agents_md"].write_text("# Index\n")
        (repo["docs_dir"] / "arch.md").write_text("See [Nope](nonexistent.md)\n")
        assert check_broken_links(**repo) == 1

    def test_valid_link_in_doc(self, repo):
        repo["agents_md"].write_text("# Index\n")
        (repo["docs_dir"] / "a.md").write_text("See [B](b.md)\n")
        (repo["docs_dir"] / "b.md").write_text("# B\n")
        assert check_broken_links(**repo) == 0

    def test_no_agents_md(self, repo):
        assert check_broken_links(**repo) == 0


# ---- check_orphan_docs ----


class TestOrphanDocs:
    def test_clean(self, repo):
        (repo["docs_dir"] / "arch.md").write_text("# Arch\n")
        repo["agents_md"].write_text("See [Arch](.agents/docs/arch.md)\n")
        assert check_orphan_docs(**repo) == 0

    def test_orphan_detected(self, repo):
        (repo["docs_dir"] / "arch.md").write_text("# Arch\n")
        (repo["docs_dir"] / "secret.md").write_text("# Hidden\n")
        repo["agents_md"].write_text("See [Arch](.agents/docs/arch.md)\n")
        assert check_orphan_docs(**repo) == 1

    def test_no_docs_dir(self, repo):
        import shutil

        shutil.rmtree(repo["docs_dir"])
        repo["agents_md"].write_text("# Index\n")
        assert check_orphan_docs(**repo) == 0

    def test_no_agents_md(self, repo):
        (repo["docs_dir"] / "arch.md").write_text("# Arch\n")
        assert check_orphan_docs(**repo) == 0


# ---- _extract_paragraphs ----


class TestExtractParagraphs:
    def test_skips_headings_and_bullets(self):
        text = textwrap.dedent("""\
            # Heading

            - bullet point

            This is a real paragraph that is long enough to pass the minimum length threshold for checking.
        """)
        paras = _extract_paragraphs(text)
        assert len(paras) == 1
        assert "real paragraph" in paras[0]

    def test_skips_code_blocks(self):
        text = textwrap.dedent("""\
            ```bash
            make test
            ```

            This is a real paragraph that is long enough to pass the minimum length threshold for checking.
        """)
        paras = _extract_paragraphs(text)
        assert len(paras) == 1
        assert "make test" not in paras[0]

    def test_skips_short_paragraphs(self):
        text = "Short.\n\nAlso short.\n"
        assert _extract_paragraphs(text) == []

    def test_joins_multiline_paragraph(self):
        text = (
            "This is the first line of a paragraph that will be joined together "
            "with the second line.\n"
            "This is the second line of that same paragraph which continues the thought.\n"
        )
        paras = _extract_paragraphs(text)
        assert len(paras) == 1
        assert "first line" in paras[0]
        assert "second line" in paras[0]


# ---- check_duplication ----


class TestDuplication:
    def test_clean_no_overlap(self, repo):
        repo["agents_md"].write_text(
            "This is unique content in the index file that does not appear anywhere else "
            "in the documentation tree at all.\n"
        )
        (repo["docs_dir"] / "arch.md").write_text(
            "This is completely different content about architecture that shares nothing "
            "with the index file whatsoever.\n"
        )
        assert check_duplication(**repo) == 0

    def test_duplicate_detected(self, repo):
        shared = (
            "Tests use Django's test runner not pytest. The Makefile creates a test game dir "
            "runs migrations then runs evennia test with keepdb.\n"
        )
        repo["agents_md"].write_text(shared)
        (repo["docs_dir"] / "testing.md").write_text(shared)
        assert check_duplication(**repo) >= 1

    def test_no_docs_dir(self, repo):
        import shutil

        shutil.rmtree(repo["docs_dir"])
        repo["agents_md"].write_text("# Index\n")
        assert check_duplication(**repo) == 0


# ---- check_stale_references ----


class TestStaleReferences:
    def test_valid_slash_path(self, repo):
        (repo["src_dir"] / "objects").mkdir()
        repo["agents_md"].write_text("Models in `objects/models.py` etc.\n")
        # create the file so it resolves
        (repo["src_dir"] / "objects" / "models.py").write_text("")
        assert check_stale_references(**repo) == 0

    def test_stale_slash_path(self, repo):
        repo["agents_md"].write_text("See `objects/nonexistent/` for details.\n")
        assert check_stale_references(**repo) == 1

    def test_valid_dotted_module(self, repo):
        mod_dir = repo["repo_root"] / "evennia" / "objects"
        mod_dir.mkdir(parents=True, exist_ok=True)
        (mod_dir / "tests.py").write_text("")
        repo["agents_md"].write_text("Run `evennia.objects.tests` for tests.\n")
        assert check_stale_references(**repo) == 0

    def test_stale_dotted_module(self, repo):
        repo["agents_md"].write_text("Run `evennia.nonexistent.module` for details.\n")
        assert check_stale_references(**repo) == 1

    def test_bare_filenames_ignored(self, repo):
        repo["agents_md"].write_text("Edit `cmdhandler.py` and use `uv` to install.\n")
        assert check_stale_references(**repo) == 0

    def test_contrib_path_resolved(self, repo):
        contrib = repo["src_dir"] / "contrib" / "base_systems"
        contrib.mkdir(parents=True)
        repo["agents_md"].write_text("See `base_systems/` in contrib.\n")
        assert check_stale_references(**repo) == 0

    def test_game_template_path_resolved(self, repo):
        tmpl = repo["src_dir"] / "game_template" / "server" / "conf"
        tmpl.mkdir(parents=True)
        (tmpl / "settings.py").write_text("")
        repo["agents_md"].write_text("Games override in `server/conf/settings.py`.\n")
        assert check_stale_references(**repo) == 0

    def test_no_agents_md(self, repo):
        assert check_stale_references(**repo) == 0

    def test_checks_docs_dir_files_too(self, repo):
        repo["agents_md"].write_text("# Index\n")
        (repo["docs_dir"] / "arch.md").write_text("See `gone/deleted/` for info.\n")
        assert check_stale_references(**repo) == 1


# ---- check_index_density ----


class TestIndexDensity:
    def test_mostly_structural(self, repo):
        repo["agents_md"].write_text(textwrap.dedent("""\
            # AGENTS.md

            ## Section

            - [Link](foo.md)
            - [Link](bar.md)

            ```bash
            make test
            ```
        """))
        assert check_index_density(**repo) == 0

    def test_too_much_prose(self, repo):
        # All non-structural lines
        prose_lines = [f"This is prose line number {i}." for i in range(30)]
        repo["agents_md"].write_text("\n".join(prose_lines) + "\n")
        assert check_index_density(**repo) == 1

    def test_no_agents_md(self, repo):
        assert check_index_density(**repo) == 0

    def test_empty_file(self, repo):
        repo["agents_md"].write_text("")
        assert check_index_density(**repo) == 0

    def test_code_block_contents_are_structural(self, repo):
        repo["agents_md"].write_text(textwrap.dedent("""\
            # AGENTS.md

            ```bash
            make test
            make format
            uv pip install -e .
            ```

            One prose line here.
        """))
        assert check_index_density(**repo) == 0
