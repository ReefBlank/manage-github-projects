#!/usr/bin/env python3
"""Unit tests for the bundled manage-github-projects scripts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import repo_doctor  # noqa: E402
import validate_project_state  # noqa: E402
import validate_skill  # noqa: E402


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def init_repo(root: Path) -> None:
    assert git(root, "init", "-q").returncode == 0
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test User")


class InitProjectStateTests(unittest.TestCase):
    def test_creates_state_files_and_does_not_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "init_project_state.py"), str(project)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            state = project / "docs" / "github"
            for name in validate_project_state.REQUIRED_FILES:
                self.assertTrue((state / name).is_file(), name)

            marker = "# 我的自定义规划\n"
            (state / "progress.md").write_text(marker, encoding="utf-8")
            second = subprocess.run(
                [sys.executable, str(SCRIPTS / "init_project_state.py"), str(project)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual((state / "progress.md").read_text(encoding="utf-8"), marker)

    def test_missing_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope"
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "init_project_state.py"), str(missing)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(result.returncode, 1)


class ValidateProjectStateTests(unittest.TestCase):
    def test_accepts_freshly_initialized_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            subprocess.run(
                [sys.executable, str(SCRIPTS / "init_project_state.py"), str(project)],
                capture_output=True,
                check=True,
            )
            self.assertEqual(validate_project_state.check_state_directory(project), [])

    def test_missing_state_directory_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            errors = validate_project_state.check_state_directory(Path(tmp))
            self.assertTrue(any("state directory is missing" in item for item in errors))

    def test_detects_credential_in_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            subprocess.run(
                [sys.executable, str(SCRIPTS / "init_project_state.py"), str(project)],
                capture_output=True,
                check=True,
            )
            fake_token = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
            (project / "docs" / "github" / "decisions.md").write_text(
                f"# 决策记录\n\ntoken={fake_token}\n", encoding="utf-8"
            )
            errors = validate_project_state.check_state_directory(project)
            self.assertTrue(any("real credential" in item for item in errors), errors)


class RepoDoctorTests(unittest.TestCase):
    def test_non_git_directory_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = repo_doctor.build_report(Path(tmp))
            self.assertTrue(report["blocked"])
            self.assertTrue(any(item["area"] == "仓库" for item in report["findings"]))

    def test_clean_repo_passes_without_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_repo(root)
            (root / "README.md").write_text("# demo\n", encoding="utf-8")
            (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
            (root / ".gitignore").write_text("node_modules/\n.env\n", encoding="utf-8")
            (root / "main.py").write_text("print('hi')\n", encoding="utf-8")
            self.assertEqual(git(root, "add", "-A").returncode, 0)
            self.assertEqual(git(root, "commit", "-qm", "init").returncode, 0)
            git(root, "remote", "add", "origin", "https://example.com/demo.git")

            report = repo_doctor.build_report(root)
            self.assertFalse(report["blocked"], report["findings"])
            self.assertTrue(any(item["message"].startswith("README.md 存在") for item in report["findings"]))

    def test_missing_license_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_repo(root)
            (root / "README.md").write_text("# demo\n", encoding="utf-8")
            report = repo_doctor.build_report(root)
            self.assertTrue(any(item["message"] == "LICENSE 缺失" for item in report["findings"]))

    def test_detects_tracked_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_repo(root)
            (root / "README.md").write_text("# demo\n", encoding="utf-8")
            (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
            (root / ".gitignore").write_text(".env\n", encoding="utf-8")
            fake = "gh" + "p_" + "Zz9Yy8Xx7Ww6Vv5Uu4Tt3Ss2Rr1Qq0Pp9Oo8"
            (root / "config.py").write_text(f'TOKEN = "{fake}"\n', encoding="utf-8")
            git(root, "add", "-A")
            report = repo_doctor.build_report(root)
            hits = [item for item in report["findings"] if item["area"] == "敏感信息扫描"]
            self.assertEqual(len(hits), 1, report["findings"])
            self.assertEqual(hits[0]["severity"], repo_doctor.BLOCK)
            self.assertNotIn(fake, json.dumps(report, ensure_ascii=False))

    def test_placeholder_tokens_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_repo(root)
            line = 'TOKEN = "gh' + 'p_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"\n'
            (root / "config.py").write_text(line, encoding="utf-8")
            git(root, "add", "-A")
            findings = repo_doctor.scan_secrets(root, repo_doctor.tracked_files(root))
            self.assertEqual(findings, [])

    def test_detects_junk_and_large_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_repo(root)
            junk = root / "node_modules" / "pkg"
            junk.mkdir(parents=True)
            (junk / "index.js").write_text("module.exports = 1\n", encoding="utf-8")
            big = root / "blob.bin"
            with big.open("wb") as handle:
                handle.seek(repo_doctor.LARGE_FILE_ADVICE_BYTES + 1)
                handle.write(b"\0")
            files = ["node_modules/pkg/index.js", "blob.bin"]
            self.assertTrue(repo_doctor.check_junk(files))
            self.assertTrue(repo_doctor.check_large_files(root, files))

    def test_severity_ordering(self) -> None:
        self.assertLess(repo_doctor.SEVERITY_ORDER[repo_doctor.BLOCK], repo_doctor.SEVERITY_ORDER[repo_doctor.PASS])


class ValidateSkillTests(unittest.TestCase):
    def test_skill_repository_is_valid(self) -> None:
        errors = validate_skill.check_structure(SKILL_ROOT)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_script_shebangs_are_present(self) -> None:
        for script in sorted((SKILL_ROOT / "scripts").glob("*.py")):
            text = script.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("#!"), script.name)


if __name__ == "__main__":
    unittest.main()
