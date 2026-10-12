#!/usr/bin/env python3
"""Initialize the persistent GitHub project state files without overwriting user work."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path, help="root of the target git project")
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    if not project_dir.is_dir():
        print(f"ERROR: project directory does not exist: {project_dir}")
        return 1

    skill_dir = Path(__file__).resolve().parent.parent
    template_dir = skill_dir / "assets" / "project-docs"
    if not template_dir.is_dir():
        print(f"ERROR: template directory is missing: {template_dir}")
        return 1

    output_dir = project_dir / "docs" / "github"
    output_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    for source in sorted(template_dir.glob("*.md")):
        target = output_dir / source.name
        if target.exists():
            print(f"SKIP: {target}")
            continue
        shutil.copy2(source, target)
        created += 1
        print(f"CREATE: {target}")

    print(f"OK: {created} file(s) created under {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
