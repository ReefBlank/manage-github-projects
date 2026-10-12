#!/usr/bin/env python3
"""Read-only GitHub repository health check for the 阶段 3「合规」 gate.

Inspects a local git working tree and reports findings graded as
阻塞 / 建议 / 可选 / 通过. Never mutates the repository, never contacts the
network, never prints file contents that could contain a credential.

Exit code 0 when no 阻塞 finding is present, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

BLOCK = "阻塞"
ADVICE = "建议"
OPTIONAL = "可选"
PASS = "通过"
SEVERITY_ORDER = {BLOCK: 0, ADVICE: 1, OPTIONAL: 2, PASS: 3}

LARGE_FILE_ADVICE_BYTES = 5 * 1024 * 1024
LARGE_FILE_BLOCK_BYTES = 50 * 1024 * 1024

COMMUNITY_FILES = {
    "README.md": (BLOCK, "仓库说明：让陌生人知道这是什么、怎么用"),
    "LICENSE": (BLOCK, "许可证：没有许可证等于保留全部权利，别人不能合法复用"),
    "CONTRIBUTING.md": (ADVICE, "贡献指南：说明如何提交改动"),
    "CODE_OF_CONDUCT.md": (ADVICE, "行为准则：明确社区预期"),
    "SECURITY.md": (ADVICE, "安全策略：说明如何报告漏洞"),
    "CHANGELOG.md": (ADVICE, "变更日志：发布时的事实来源"),
    ".gitignore": (BLOCK, "忽略规则：避免提交构建产物与本地文件"),
}

TEMPLATE_FILES = {
    ".github/ISSUE_TEMPLATE": OPTIONAL,
    ".github/PULL_REQUEST_TEMPLATE.md": OPTIONAL,
    ".github/workflows": ADVICE,
    ".github/dependabot.yml": OPTIONAL,
    ".gitattributes": OPTIONAL,
}

JUNK_PATTERNS = [
    (re.compile(r"(^|/)node_modules/"), "依赖目录"),
    (re.compile(r"(^|/)(dist|build|out|target)/"), "构建产物"),
    (re.compile(r"(^|/)__pycache__/"), "Python 缓存"),
    (re.compile(r"\.pyc$"), "Python 字节码"),
    (re.compile(r"(^|/)\.venv/|(^|/)venv/"), "虚拟环境"),
    (re.compile(r"(^|/)\.env$|(^|/)\.env\.(local|dev|prod)$"), "本地环境文件"),
    (re.compile(r"\.(log|zip|tar\.gz|rar|7z)$"), "日志或打包文件"),
    (re.compile(r"(^|/)\.DS_Store$|(^|/)Thumbs\.db$"), "系统文件"),
    (re.compile(r"\.(pem|key|p12|pfx)$|(^|/)id_rsa"), "密钥类文件"),
]

SECRET_PATTERNS = [
    (re.compile("gh" + "[pousr]_[A-Za-z0-9]{20,}"), "GitHub token"),
    (re.compile("github" + "_pat_[A-Za-z0-9_]{20,}"), "GitHub 细粒度 token"),
    (re.compile("AKIA" + "[0-9A-Z]{16}"), "AWS access key"),
    (re.compile("-----BEGIN " + "[A-Z ]*PRIVATE KEY-----"), "私钥文件内容"),
    (re.compile("sk" + "-[A-Za-z0-9]{24,}"), "API key"),
]

PLACEHOLDER_MARKERS = ("xxx", "XXXX", "<", "your", "示例", "例如", "placeholder", "REDACTED", "***")

TEXT_SUFFIXES = {
    ".md", ".txt", ".json", ".jsonc", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".env", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".rb", ".go", ".rs",
    ".java", ".kt", ".cs", ".php", ".sh", ".ps1", ".bat", ".sql", ".xml", ".html", ".css",
}

MAX_SCAN_BYTES = 512 * 1024


@dataclass
class Finding:
    severity: str
    area: str
    message: str
    hint: str = ""


def run_git(root: Path, *args: str) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as error:  # pragma: no cover - env dependent
        return 127, str(error)
    return completed.returncode, completed.stdout


def is_git_repo(root: Path) -> bool:
    code, out = run_git(root, "rev-parse", "--is-inside-work-tree")
    return code == 0 and out.strip() == "true"


def tracked_files(root: Path) -> list[str]:
    code, out = run_git(root, "ls-files", "-z")
    if code != 0:
        return []
    return [name for name in out.split("\0") if name]


def is_placeholder(text: str) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in PLACEHOLDER_MARKERS)


def scan_secrets(root: Path, files: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for relative in files:
        path = root / relative
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {".env", ".gitignore"}:
            continue
        try:
            if path.stat().st_size > MAX_SCAN_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if is_placeholder(line):
                continue
            for pattern, label in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        Finding(
                            BLOCK,
                            "敏感信息扫描",
                            f"{relative}:{line_number} 命中疑似 {label}",
                            "推送前必须处置：轮换密钥、移出仓库、确认历史是否需要清理（危险操作，需单项授权）",
                        )
                    )
                    break
    return findings


def check_large_files(root: Path, files: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for relative in files:
        path = root / relative
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size >= LARGE_FILE_BLOCK_BYTES:
            findings.append(
                Finding(BLOCK, "体积体检", f"{relative} 约 {size / 1024 / 1024:.1f} MiB", "考虑 Git LFS 或改为 Release 附件")
            )
        elif size >= LARGE_FILE_ADVICE_BYTES:
            findings.append(
                Finding(ADVICE, "体积体检", f"{relative} 约 {size / 1024 / 1024:.1f} MiB", "确认是否必要，避免仓库长期膨胀")
            )
    return findings


def check_junk(files: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()
    for relative in files:
        for pattern, label in JUNK_PATTERNS:
            if pattern.search(relative):
                if label in seen:
                    break
                seen.add(label)
                findings.append(
                    Finding(ADVICE, "忽略规则", f"已跟踪疑似{label}：{relative}", "加入 .gitignore 并用 git rm --cached 移出索引")
                )
                break
    return findings


def check_community(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for name, (severity, hint) in COMMUNITY_FILES.items():
        if (root / name).is_file():
            findings.append(Finding(PASS, "合规文件", f"{name} 存在"))
        else:
            findings.append(Finding(severity, "合规文件", f"{name} 缺失", hint))
    for name, severity in TEMPLATE_FILES.items():
        path = root / name
        if path.is_dir() and any(path.iterdir()):
            findings.append(Finding(PASS, "社区模板", f"{name} 已配置"))
        elif path.is_file():
            findings.append(Finding(PASS, "社区模板", f"{name} 已配置"))
        else:
            findings.append(Finding(severity, "社区模板", f"{name} 未配置", "提升协作与自动化体验"))
    return findings


def check_remote(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    code, out = run_git(root, "remote", "-v")
    if code != 0 or not out.strip():
        findings.append(Finding(BLOCK, "远程", "没有配置任何远程仓库", "git remote add origin <url>"))
        return findings
    findings.append(Finding(PASS, "远程", "已配置远程：" + " ".join(sorted({line.split()[0] for line in out.splitlines() if line.strip()}))))
    if "origin" not in {line.split()[0] for line in out.splitlines() if line.strip()}:
        findings.append(Finding(ADVICE, "远程", "远程名称不是 origin", "约定使用 origin 便于协作"))
    return findings


def check_branch_and_tags(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    code, out = run_git(root, "symbolic-ref", "--short", "HEAD")
    branch = out.strip() if code == 0 else ""
    if not branch:
        findings.append(Finding(ADVICE, "分支", "当前处于游离 HEAD", "切回默认分支再操作"))
    elif branch in {"master"}:
        findings.append(Finding(ADVICE, "分支", "默认分支为 master", "新仓库建议使用 main，重命名属于危险操作需单项授权"))
    else:
        findings.append(Finding(PASS, "分支", f"当前分支 {branch}"))

    code, out = run_git(root, "status", "--porcelain")
    if code == 0:
        dirty = [line for line in out.splitlines() if line.strip()]
        if dirty:
            findings.append(Finding(ADVICE, "工作区", f"有 {len(dirty)} 项未提交改动", "先提交或 stash，避免发布时版本与工作区不一致"))
        else:
            findings.append(Finding(PASS, "工作区", "工作区干净"))

    code, out = run_git(root, "tag", "--list")
    tags = [line for line in out.splitlines() if line.strip()]
    if tags:
        findings.append(Finding(PASS, "版本", f"已有 {len(tags)} 个 tag，最新 {tags[-1]}"))
    else:
        findings.append(Finding(OPTIONAL, "版本", "尚无 tag", "首次发布时按语义化版本创建"))
    return findings


def check_ci(root: Path) -> list[Finding]:
    workflow_dir = root / ".github" / "workflows"
    findings: list[Finding] = []
    if workflow_dir.is_dir() and any(workflow_dir.glob("*.y*ml")):
        findings.append(Finding(PASS, "CI", "已有 GitHub Actions 工作流"))
    else:
        findings.append(Finding(ADVICE, "CI", "没有 CI 工作流", "至少加一个只读校验任务"))
    return findings


def build_report(root: Path) -> dict:
    findings: list[Finding] = []
    if not is_git_repo(root):
        findings.append(Finding(BLOCK, "仓库", "目标目录不是 git 仓库", "先按 阶段 2「建仓」初始化"))
        return summarize(root, findings, [])

    files = tracked_files(root)
    findings.extend(check_remote(root))
    findings.extend(check_branch_and_tags(root))
    findings.extend(check_community(root))
    findings.extend(check_ci(root))
    findings.extend(scan_secrets(root, files))
    findings.extend(check_large_files(root, files))
    findings.extend(check_junk(files))
    findings.append(Finding(PASS, "仓库", f"已跟踪 {len(files)} 个文件"))
    return summarize(root, findings, files)


def summarize(root: Path, findings: list[Finding], files: list[str]) -> dict:
    findings.sort(key=lambda item: (SEVERITY_ORDER[item.severity], item.area))
    counts = {severity: 0 for severity in SEVERITY_ORDER}
    for finding in findings:
        counts[finding.severity] += 1
    return {
        "root": str(root),
        "trackedFileCount": len(files),
        "counts": counts,
        "findings": [asdict(finding) for finding in findings],
        "blocked": counts[BLOCK] > 0,
    }


def render(report: dict) -> None:
    print(f"仓库体检报告：{report['root']}")
    print(f"已跟踪文件：{report['trackedFileCount']}")
    print("=" * 72)
    for severity in (BLOCK, ADVICE, OPTIONAL, PASS):
        rows = [item for item in report["findings"] if item["severity"] == severity]
        if not rows:
            continue
        print(f"\n## {severity}（{len(rows)}）")
        for item in rows:
            print(f"  - [{item['area']}] {item['message']}")
            if item["hint"]:
                print(f"      处理建议：{item['hint']}")
    counts = report["counts"]
    print("\n" + "=" * 72)
    print(
        "统计：阻塞 {阻塞} / 建议 {建议} / 可选 {可选} / 通过 {通过}".format(**counts)
    )
    if report["blocked"]:
        print("结论：存在阻塞项，先清零再进入发布阶段。")
    else:
        print("结论：无阻塞项。该结论为 L1 静态证据，不代表远程状态或 CI 结论。")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path, help="root of the git project to inspect")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = parser.parse_args()

    root = args.project_dir.resolve()
    if not root.is_dir():
        print(f"ERROR: project directory does not exist: {root}")
        return 1

    report = build_report(root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        render(report)
    return 1 if report["blocked"] else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:  # pragma: no cover - non-standard stdout
        pass
    sys.exit(main())
