#!/usr/bin/env python3
"""Validate the persistent GitHub project state files.

Read-only. Reports structure problems and refused content (credentials must never
be written into project state files).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_FILES = [
    "project-plan.md",
    "progress.md",
    "decisions.md",
    "version-change.md",
    "test-report.md",
    "release-checklist.md",
]

# Fragments are assembled at runtime so this file never contains a literal token
# prefix that a secret scanner would flag.
SECRET_PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9]{24,}"),
]

PLACEHOLDER_MARKERS = ("xxx", "XXXX", "<", "your", "示例", "例如", "placeholder", "REDACTED", "…", "***")


def check_state_directory(root: Path) -> list[str]:
    errors: list[str] = []
    state_dir = root / "docs" / "github"
    if not state_dir.is_dir():
        return [f"state directory is missing: {state_dir} (run scripts/init_project_state.py)"]

    for name in REQUIRED_FILES:
        path = state_dir / name
        if not path.is_file():
            errors.append(f"missing state file: docs/github/{name}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.lstrip().startswith("# "):
            errors.append(f"docs/github/{name} must start with an H1 heading")
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                line = text[: match.start()].count("\n") + 1
                errors.append(
                    f"docs/github/{name}:{line} looks like a real credential; "
                    "project state must not contain passwords, tokens or private keys"
                )
    return errors


def check_placeholders(root: Path) -> list[str]:
    notes: list[str] = []
    state_dir = root / "docs" / "github"
    if not state_dir.is_dir():
        return notes
    for path in sorted(state_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in ("TODO", "待补充", "FIXME"):
            if marker in text:
                line = text[: text.index(marker)].count("\n") + 1
                notes.append(f"docs/github/{path.name}:{line} still contains '{marker}'")
    return notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path, help="root of the target git project")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat unfinished placeholders as errors instead of notes",
    )
    args = parser.parse_args()

    root = args.project_dir.resolve()
    if not root.is_dir():
        print(f"ERROR: project directory does not exist: {root}")
        return 1

    errors = check_state_directory(root)
    notes = check_placeholders(root)
    if args.strict:
        errors.extend(notes)
        notes = []

    for error in errors:
        print(f"ERROR: {error}")
    for note in notes:
        print(f"NOTE: {note}")
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print(f"OK: project state is valid under {root / 'docs' / 'github'}")
    if notes:
        print(f"OK with {len(notes)} note(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
