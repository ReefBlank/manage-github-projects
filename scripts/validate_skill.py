#!/usr/bin/env python3
"""Validate the manage-github-projects skill structure and behavior markers.

Run from the skill root:

    python scripts/validate_skill.py .
    python scripts/validate_skill.py . --check-links
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "LICENSE",
    "agents/openai.yaml",
    ".github/workflows/validate.yml",
    "references/auth-and-safety.md",
    "references/repo-setup-stage.md",
    "references/repo-audit.md",
    "references/release-stage.md",
    "references/maintenance.md",
    "references/state-persistence.md",
    "references/acceptance-tests.md",
    "references/official-links.md",
    "assets/project-docs/project-plan.md",
    "assets/project-docs/progress.md",
    "assets/project-docs/decisions.md",
    "assets/project-docs/version-change.md",
    "assets/project-docs/test-report.md",
    "assets/project-docs/release-checklist.md",
    "scripts/init_project_state.py",
    "scripts/validate_project_state.py",
    "scripts/repo_doctor.py",
    "tests/test_scripts.py",
]

REQUIRED_PHRASES = [
    "接入",
    "建仓",
    "合规",
    "发布",
    "目标信息收齐",
    "公开范围确认",
    "首推范围确认",
    "发布方案确认",
    "危险操作单项授权",
    "force push",
    "git filter-repo",
    "不索取密码",
    "不索取验证码",
    "personal access token",
    "脱敏",
    "敏感信息扫描",
    "体积体检",
    "Git LFS",
    "语义化版本",
    "已发布的 tag 不得移动",
    "版本号一致性",
    "CHANGELOG.md",
    "GitHub Release",
    "README.md",
    "LICENSE",
    "LICENSE 文本必须与用户选定的一致",
    "阻塞 / 建议 / 可选 / 通过",
    "repo_doctor.py",
    "validate_project_state.py",
    "state-persistence.md",
    "docs/github/",
    "证据等级",
    "L1 静态",
    "L5",
    "低等级证据不得冒充高等级",
    "阻塞项未清零前，不进入发布阶段",
    "用户只回复泛化词时，重复当前门禁和待确认项，不得推进",
    "userask",
    "结构化提问工具",
    "立即回退为编号文字",
    "我操作",
    "你操作",
    "截图或报错文字",
    "不得代替用户完成登录",
    "不得编造功能",
    "已有仓库不要重复初始化",
]

CONTENT_ASSERTIONS = {
    "references/repo-setup-stage.md": [
        "git init",
        "git remote add origin",
        "git push -u origin",
        "默认分支",
        "main",
        ".gitignore",
        "敏感信息扫描",
        "体积体检",
        "Git LFS",
        "git filter-repo",
        "危险操作单项授权",
        "首推范围确认",
        "创建远程仓库",
        "同名仓库",
        "git config user.name",
        "git config user.email",
        "证据等级",
        "不要先推上去再删",
        "`git status`",
    ],
    "references/release-stage.md": [
        "语义化版本",
        "git tag -a",
        "GitHub Release",
        "CHANGELOG.md",
        "release notes",
        "预发布",
        "已发布的 tag 不得移动",
        "版本号一致性",
        "package.json",
        "发布方案确认",
        "回滚",
        "证据等级",
        "L5",
        "不得编造",
    ],
    "references/maintenance.md": [
        "Conventional Commits",
        "提交规范",
        "分支策略",
        "issue",
        "pull request",
        "标签",
        "里程碑",
        "依赖更新",
        "Dependabot",
        "归档",
        "危险操作单项授权",
        "不得代替用户提交",
        "CODEOWNERS",
    ],
    "references/repo-audit.md": [
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "Issue 模板",
        "Pull Request 模板",
        "分支保护",
        "Dependabot",
        "secret scanning",
        "许可证兼容",
        "体检报告",
        "阻塞 / 建议 / 可选 / 通过",
        "repo_doctor.py",
        "证据等级",
    ],
    "references/auth-and-safety.md": [
        "凭据",
        "不索取密码",
        "不索取验证码",
        "personal access token",
        "credential.helper",
        "SSH",
        "最小权限",
        "不得把 token 写入仓库",
        "危险操作默认安全跳过",
        "force push",
        "删除仓库",
        "更改可见性",
        "单项授权",
        "git credential fill",
        "git filter-repo",
        "轮换",
        "脱敏",
    ],
    "references/state-persistence.md": [
        "project-plan.md",
        "progress.md",
        "decisions.md",
        "version-change.md",
        "test-report.md",
        "release-checklist.md",
        "docs/github/",
        "validate_project_state.py",
        "禁止记录密码",
        "init_project_state.py",
        "非秘密标识",
    ],
    "assets/project-docs/project-plan.md": [
        "仓库名",
        "可见性",
        "许可证",
        "默认分支",
        "目标平台",
    ],
    "assets/project-docs/progress.md": [
        "接入",
        "建仓",
        "合规",
        "发布",
    ],
    "assets/project-docs/release-checklist.md": [
        "版本号一致性",
        "CHANGELOG",
        "证据等级",
        "危险操作",
    ],
}

FORBIDDEN_PHRASES = [
    "TODO",
    "待补充",
    "优先读取 `ui-ux-pro-max`",
]

SKILL_NAME = "manage-github-projects"


def extract_urls(path: Path) -> list[str]:
    return re.findall(r"https?://[^)\s>]+", path.read_text(encoding="utf-8"))


def check_local_markdown_links(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    for markdown in skill_dir.rglob("*.md"):
        content = markdown.read_text(encoding="utf-8")
        for target in re.findall(r"\]\((?!https?://)([^)]+)\)", content):
            relative = target.split("#", 1)[0]
            if not relative:
                continue
            resolved = (markdown.parent / relative).resolve()
            if not resolved.exists():
                errors.append(f"broken local link in {markdown.relative_to(skill_dir)}: {target}")
    return errors


def check_structure(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        if not (skill_dir / relative).is_file():
            errors.append(f"missing file: {relative}")

    skill = skill_dir / "SKILL.md"
    if skill.is_file():
        content = skill.read_text(encoding="utf-8")
        if not content.startswith("---\n") or "\n---\n" not in content:
            errors.append("SKILL.md must have YAML frontmatter")
        frontmatter = content.split("\n---\n", 1)[0]
        if not re.search(rf"^name:\s*{SKILL_NAME}\s*$", frontmatter, re.M):
            errors.append("frontmatter name is incorrect")
        if not re.search(r"^description:\s*.+", frontmatter, re.M):
            errors.append("frontmatter description is missing")
        for phrase in REQUIRED_PHRASES:
            if phrase not in content:
                errors.append(f"SKILL.md missing required phrase: {phrase}")

    for relative, phrases in CONTENT_ASSERTIONS.items():
        path = skill_dir / relative
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in content:
                errors.append(f"{relative} missing behavior assertion: {phrase}")

    acceptance = skill_dir / "references" / "acceptance-tests.md"
    if acceptance.is_file():
        content = acceptance.read_text(encoding="utf-8")
        for number in range(1, 41):
            test_id = f"T{number:02d}"
            if test_id not in content:
                errors.append(f"acceptance test missing: {test_id}")
        for column in ("编号", "场景", "操作", "预期结果", "证据等级"):
            if column not in content:
                errors.append(f"acceptance-tests.md missing table column: {column}")

    for markdown in skill_dir.rglob("*.md"):
        content = markdown.read_text(encoding="utf-8")
        for phrase in FORBIDDEN_PHRASES:
            if phrase in content:
                errors.append(f"forbidden phrase in {markdown.relative_to(skill_dir)}: {phrase}")

    for script in sorted((skill_dir / "scripts").glob("*.py")) if (skill_dir / "scripts").is_dir() else []:
        text = script.read_text(encoding="utf-8")
        if not text.startswith("#!"):
            errors.append(f"script missing shebang: {script.relative_to(skill_dir)}")

    links = skill_dir / "references" / "official-links.md"
    if links.is_file():
        urls = extract_urls(links)
        if len(urls) < 20:
            errors.append(f"official-links.md must contain at least 20 verified URLs (found {len(urls)})")
        if "核验日期" not in links.read_text(encoding="utf-8"):
            errors.append("official-links.md must record 核验日期")

    agents = skill_dir / "agents" / "openai.yaml"
    if agents.is_file():
        text = agents.read_text(encoding="utf-8")
        for key in ("display_name:", "short_description:", "default_prompt:"):
            if key not in text:
                errors.append(f"agents/openai.yaml missing key: {key}")

    errors.extend(check_local_markdown_links(skill_dir))
    return errors


def check_links(skill_dir: Path) -> list[str]:
    link_file = skill_dir / "references/official-links.md"
    errors: list[str] = []
    for url in extract_urls(link_file):
        request = Request(url, method="HEAD", headers={"User-Agent": "manage-github-projects-link-check/1.0"})
        try:
            with urlopen(request, timeout=15) as response:
                status = response.status
        except HTTPError as error:
            status = error.code
        except (URLError, TimeoutError, OSError) as error:
            errors.append(f"{url}: {error}")
            continue
        if status < 200 or status >= 400:
            errors.append(f"{url}: HTTP {status}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("--check-links", action="store_true")
    args = parser.parse_args()
    skill_dir = args.skill_dir.resolve()

    errors = check_structure(skill_dir)
    if args.check_links and not errors:
        errors.extend(check_links(skill_dir))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {skill_dir}")
    if args.check_links:
        print("OK: official links")
    return 0


if __name__ == "__main__":
    sys.exit(main())
