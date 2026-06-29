"""A tiny loader for filesystem 'skills' (analyst playbooks).

A skill is a folder with a SKILL.md: YAML frontmatter (name + description — the
part a formal Anthropic Agent Skill keeps in context at all times so the model
knows the skill exists) plus a markdown body (the full playbook, loaded only
when the task is relevant). Here we load the body and use it as the analysis
system prompt. The identical SKILL.md could be uploaded via Anthropic's Skills
API to become a versioned Agent Skill — same format, no rewrite.
"""

from __future__ import annotations

from pathlib import Path

_SKILLS_DIR = Path(__file__).parent / "skills"


def load_skill(name: str) -> str:
    """Return the markdown body of a skill (frontmatter stripped)."""
    text = (_SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].strip()
    return text.strip()
