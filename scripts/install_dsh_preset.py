#!/usr/bin/env python3
"""Install this skill into a DeepSeek Harness user profile.

Copies the skill repository root to `<skills-dir>/manage-github-projects` and
creates the matching agent preset under `<presets-dir>/manage-github-projects`
(with the skill carried in its own `skills/` directory, as DSH presets expect).

Nothing is overwritten unless `--force` is given.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SKILL_NAME = "manage-github-projects"
EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}
EXCLUDED_FILES = {".DS_Store", "Thumbs.db"}


def ignore(directory: str, names: list[str]) -> set[str]:
    del directory
    return {name for name in names if name in EXCLUDED_DIRS or name in EXCLUDED_FILES}


def copy_skill(source: Path, target: Path, force: bool) -> list[str]:
    messages: list[str] = []
    if target.exists():
        if not force:
            raise SystemExit(
                f"ERROR: {target} already exists; inspect its version and source first, "
                "then re-run with --force to replace it"
            )
        shutil.rmtree(target)
        messages.append(f"REPLACE: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, ignore=ignore)
    messages.append(f"CREATE: {target}")
    return messages


def main() -> int:
    skill_root = Path(__file__).resolve().parent.parent
    home = Path.home()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path, default=home / ".dsh" / "skills")
    parser.add_argument("--presets-dir", type=Path, default=home / ".dsh" / ".agent-presets")
    parser.add_argument("--force", action="store_true", help="replace an existing installation")
    parser.add_argument("--skip-preset", action="store_true", help="install the skill only")
    args = parser.parse_args()

    if not (skill_root / "SKILL.md").is_file():
        print(f"ERROR: {skill_root} does not look like the skill root (SKILL.md missing)")
        return 1

    preset_source = skill_root / "preset"
    if not args.skip_preset and not (preset_source / "agent.cordis.yml").is_file():
        print(f"ERROR: preset files are missing under {preset_source}")
        return 1

    messages: list[str] = []
    skill_target = args.skills_dir.expanduser() / SKILL_NAME
    messages.extend(copy_skill(skill_root, skill_target, args.force))

    preset_target = None
    if not args.skip_preset:
        preset_target = args.presets_dir.expanduser() / SKILL_NAME
        messages.extend(copy_skill(skill_root, preset_target / "skills" / SKILL_NAME, args.force))
        preset_target.mkdir(parents=True, exist_ok=True)
        for name in ("preset.yml", "agent.cordis.yml"):
            destination = preset_target / name
            if destination.exists() and not args.force:
                raise SystemExit(f"ERROR: {destination} already exists; re-run with --force to replace it")
            shutil.copy2(preset_source / name, destination)
            messages.append(f"CREATE: {destination}")

    for message in messages:
        print(message)

    print("\n入口：")
    print(f"  {skill_target / 'SKILL.md'}")
    if preset_target is not None:
        print(f"  {preset_target / 'agent.cordis.yml'}")
        print("\n预设已安装。在 DSH 中新建会话时选择预设「GitHub 项目管理助手」即可；")
        print("预设元数据在 preset.yml 中（name / description / order）。")
    print("\n校验：")
    print(f"  python \"{skill_target / 'scripts' / 'validate_skill.py'}\" \"{skill_target}\"")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:  # pragma: no cover - non-standard stdout
        pass
    sys.exit(main())
