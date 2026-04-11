# Agent Skills

Vendor-agnostic skill definitions for AI coding agents.

Vendor-specific tools discover skills through their own directory conventions
(e.g. `.claude/skills/`, `.codex/skills/`). Those directories should be
symlinks pointing here so that skill files are maintained in one place.

## Adding a skill

Place skill files (e.g. `my-skill.md`) directly in this directory.

## Vendor symlinks

```bash
# Claude Code
mkdir -p .claude && ln -s ../.agents/skills .claude/skills

# Codex
mkdir -p .codex && ln -s ../.agents/skills .codex/skills
```
