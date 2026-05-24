"""Scan di sicurezza: il repo non deve contenere credenziali hardcoded.

Pattern controllati:
  - Anthropic API key: ``sk-ant-...``
  - AWS access key: ``AKIA[0-9A-Z]{16}``
  - Private key PEM
  - Password in stringa: ``password = "..."``

Skip:
  - File di test (``tests/``) — ammettono mock di credenziali
  - Archivio legacy (``_legacy-single-user/``)
  - Brief temporanei (``_brief/``)
  - Fixture e dataset di esempio (``_fixtures/``, ``_inbox/``, ``_pilot/``)
  - Status runtime (``_status/``)
  - Venv, cache, build
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Pattern di credenziali da bloccare
PATTERNS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"), "Anthropic API key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "Private key PEM"),
    (
        re.compile(
            r"""(?i)(password|passwd|pwd)\s*=\s*['"][^'"$\{<]{6,}['"]""",
        ),
        "Password literal",
    ),
]

EXCLUDED_DIRS = {
    "tests",
    "_legacy-single-user",
    "_brief",
    "_fixtures",
    "_inbox",
    "_pilot",
    "_status",
    ".venv",
    "venv",
    "env",
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".claude",
    "htmlcov",
    "build",
    "dist",
}

EXCLUDED_FILES = {
    "test_no_secrets.py",  # questo file contiene pattern di test
    "uv.lock",
}

INCLUDE_EXTENSIONS = {".py", ".yml", ".yaml", ".toml", ".sh", ".env", ".cfg", ".ini", ".md"}


def _iter_repo_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in INCLUDE_EXTENSIONS:
            continue
        if path.name in EXCLUDED_FILES:
            continue
        rel_parts = path.relative_to(REPO_ROOT).parts
        if any(part in EXCLUDED_DIRS for part in rel_parts):
            continue
        files.append(path)
    return files


@pytest.mark.parametrize("pattern,label", PATTERNS, ids=[label for _, label in PATTERNS])
def test_no_credentials_in_repo(pattern: re.Pattern[str], label: str) -> None:
    """Nessuna credenziale del tipo `label` deve apparire in file tracciati."""
    matches: list[str] = []
    for path in _iter_repo_files():
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in pattern.finditer(content):
            line_num = content[: m.start()].count("\n") + 1
            matches.append(f"{path.relative_to(REPO_ROOT)}:{line_num} ({m.group()[:30]}...)")
    assert not matches, f"{label} trovato in:\n  " + "\n  ".join(matches)
