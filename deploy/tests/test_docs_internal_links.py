"""Verify relative markdown links under deploy/docs/ resolve to existing paths."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCS_ROOT = _REPO_ROOT / "deploy" / "docs"
_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def test_deploy_docs_markdown_internal_targets_exist() -> None:
    assert _DOCS_ROOT.is_dir(), f"missing {_DOCS_ROOT}"
    for md in sorted(_DOCS_ROOT.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        for m in _LINK.finditer(text):
            raw = m.group(1).strip()
            if not raw or raw.startswith(("#", "http://", "https://", "mailto:")):
                continue
            path_part = raw.split("#", 1)[0].strip()
            if not path_part:
                continue
            target = (md.parent / path_part).resolve()
            assert target.exists(), (
                f"broken link in {md.relative_to(_REPO_ROOT)} → {raw!r}"
            )
