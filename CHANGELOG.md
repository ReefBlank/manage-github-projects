# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.1] - 2026-10-12

对引用手册的补充完善，不改变 Skill 的行为契约、脚本接口或预设结构。

### 变更

- `references/auth-and-safety.md`：补充 `git credential fill` 的显式标准输入用法，并新增「无法确认是否会弹出交互提示时改用 `git config --get credential.helper` 或 `gh auth status`」的约束。
- `references/state-persistence.md`：扩展为完整手册——目录布局、六个状态文件的关键字段、初始化与校验方式、更新时机、敏感信息禁写清单与冲突处理清单。
- `references/repo-audit.md`：细化体检步骤、README 审查标准、许可证兼容性判断与常见误判。

### 说明

v1.0.0 的 tag 与 Release 保持原样，未做移动或覆盖；本次修正按语义化版本发布为 1.0.1。

## [1.0.0] - 2026-10-12

首个公开版本。

### 新增

- 四阶段状态机与四道确认门禁：接入、建仓、合规、发布。
- `references/` 下的执行手册：`auth-and-safety.md`、`repo-setup-stage.md`、`repo-audit.md`、`release-stage.md`、`maintenance.md`、`state-persistence.md`。
- `references/acceptance-tests.md`：T01-T40 验收用例表。
- `references/official-links.md`：官方入口链接清单。
- `scripts/repo_doctor.py`：只读仓库体检，输出按 阻塞 / 建议 / 可选 / 通过 分级的报告，支持 `--json`。
- `scripts/validate_skill.py`：校验 Skill 结构与行为标记，支持 `--check-links`。
- `scripts/validate_project_state.py`：校验 `docs/github/` 状态文件，并拒绝把凭据写入项目状态。
- `scripts/init_project_state.py`：初始化状态文件，不覆盖已有内容。
- `scripts/install_dsh_preset.py`：一键安装到 DeepSeek Harness 用户 Skill 目录与 Agent 预设目录。
- `assets/project-docs/`：`project-plan.md`、`progress.md`、`decisions.md`、`version-change.md`、`test-report.md`、`release-checklist.md` 模板。
- DeepSeek Harness Agent 预设「GitHub 项目管理助手」（`preset/`）。
- `tests/test_scripts.py`：14 条单元测试，覆盖状态初始化、凭据拒绝、体检分级与预设结构校验。
- GitHub Actions 工作流校验 Skill 结构与单元测试。

### 安全

- 凭据只从用户已配置的环境读取，报告时脱敏；不索取密码、验证码、personal access token 或私钥。
- 推送前强制敏感信息扫描与体积体检。
- `force push`、历史重写、删除仓库、更改可见性、删除 tag 或 Release 一律需要危险操作单项授权。
