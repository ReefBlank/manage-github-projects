# 阶段 4：发布执行手册

本手册对应四阶段状态机中的「发布」阶段（第 4/4 阶段）。四阶段固定为 **接入 / 建仓 / 合规 / 发布**。

进入本阶段的前提是合规体检的**阻塞**项已清零。本阶段目标：把一个可追溯的版本发布出去——版本号唯一、tag 与清单文件一致、Release 说明来自真实变更、发布后可核验。

> 术语统一：四道门禁 =「目标信息收齐」「公开范围确认」「首推范围确认」「发布方案确认」。本阶段负责「发布方案确认」。证据等级 = L1 静态 / L2 本地 Git / L3 远程 API / L4 CI / L5 发布物。

## 阶段目标与完成标准

| 项目 | 完成标准 | 证据等级 |
| --- | --- | --- |
| 发布方案 | 用户明确回复「发布方案确认」 | — |
| 版本号 | 版本号符合**语义化版本**，且与变更性质匹配 | L1 静态 |
| 版本号一致性 | tag、`package.json`（或等价清单）、`CHANGELOG.md` 顶部、Release 标题四处一致 | L1 静态 + L2 本地 Git |
| tag | 带注解 tag 已创建并推送到远程 | L2 本地 Git + L3 远程 API |
| GitHub Release | Release 页面可访问，说明来自实际变更 | L3 远程 API |
| 发布物 | 附件可下载且可用，CI 结论正常 | L4 CI + L5 发布物 |

## 步骤 1：发布方案确认（门禁）

1. 先盘点事实，不要用记忆代替命令输出：

```bash
git log --oneline --decorate -20
git tag --list --sort=-v:refname
git status --short
gh release list --limit 10
```

2. 汇总上一版本以来的实际变更：新增功能、修复、破坏性变更、依赖调整、文档变化。
3. 给出版本变更单草案，包含：建议版本号、tag 名（默认 `v<版本号>`）、Release 标题、是否**预发布**、`CHANGELOG.md` 草案、目标提交哈希。
4. 等待用户明确回复「**发布方案确认**」。泛化回复（「下一步」「好的」「可以」）不等于通过门禁；用户只回复泛化词时，重复当前门禁与待确认项，不得推进。
5. 用户要求修改时，更新草案并重新确认，不带着未确认项执行任何写入操作。

## 步骤 2：版本号决策

版本号遵循**语义化版本** `MAJOR.MINOR.PATCH`：

| 变更性质 | 版本位 | 示例 |
| --- | --- | --- |
| 破坏性变更 | MAJOR | `1.4.2` → `2.0.0` |
| 向后兼容的新功能 | MINOR | `1.4.2` → `1.5.0` |
| 向后兼容的问题修复 | PATCH | `1.4.2` → `1.4.3` |
| 预发布 | 追加标识 | `2.0.0-rc.1`、`1.5.0-beta.2` |

规则：

1. `0.x` 表示尚不稳定，`1.0.0` 表示用户可依赖的公开 API 已稳定。不得为了好看而跳到 `1.0.0`，由用户确认后再定。
2. 已发布版本的号段不得回收复用。删掉一个 Release 后重新用同一个版本号发布新内容是禁止的。
3. 预发布版本使用 `-alpha`、`-beta`、`-rc` 这类标识，并在 GitHub Release 上勾选 pre-release。
4. 版本号是用户决策；代理给出带理由的建议，并明确标注为建议。

## 步骤 3：版本号一致性检查

1. 四个位置必须一致：tag 名、`package.json`（或 `pyproject.toml`、`Cargo.toml`、`pom.xml` 等等价清单）、`CHANGELOG.md` 顶部条目、Release 标题。
2. 检查清单文件中的版本字段：

```bash
grep -n "\"version\"" package.json
git show HEAD:package.json | grep -n "\"version\""
```

3. 检查 CHANGELOG 顶部：

```bash
head -n 20 CHANGELOG.md
```

4. 发现不一致时先列出冲突，再收敛到用户确认的版本号：

| 冲突形态 | 处置 |
| --- | --- |
| `package.json` 版本落后于 tag | 提交一次版本号更新，再打 tag |
| CHANGELOG 缺少当前版本条目 | 补齐条目后再发布 |
| tag 名缺少 `v` 前缀而历史 tag 都有 | 与历史风格保持一致，由用户确认 |
| 已存在同版本 tag 且已发布 | 停止，改为递增版本号，不得移动旧 tag |

5. 一致性属于 L1 静态与 L2 本地 Git 证据；远程是否已有该 tag 属于 L3。

## 步骤 4：CHANGELOG.md

1. 采用「最新版本在最上方」的结构，每个版本一节：

文件第一行使用一级标题 `# 更新日志`，其下每个版本一节，最新版本在最上方：

```markdown
## [1.5.0] - 2026-01-15

### 新增
- 支持配置文件热加载

### 修复
- 修正 Windows 下的路径分隔符处理

### 破坏性变更
- 移除已弃用的 `--legacy` 参数
```

2. 条目必须来自 grep 得到的实际提交与 diff，**不得编造**功能、日期、贡献者或性能数字。
3. 分类建议使用「新增 / 修复 / 变更 / 破坏性变更 / 文档 / 依赖」，与**提交规范**的分组对应，细则见 [maintenance.md](maintenance.md)。
4. CHANGELOG 顶部条目要与本次发布的版本号完全一致；日期使用实际发布日。
5. 生成后由用户复核措辞，特别是破坏性变更的迁移说明。

## 步骤 5：创建并推送 tag

1. 确认工作区干净、目标提交是预期提交：

```bash
git status --short
git rev-parse HEAD
```

2. 默认使用带注解的 tag：

```bash
git tag -a v1.5.0 -m "v1.5.0"
```

带注解 tag 会记录打 tag 者、时间与说明，便于追溯；轻量 tag 只在用户明确要求时使用。

3. 推送单个 tag，避免误推其他本地 tag：

```bash
git push origin v1.5.0
```

4. 核验远程 tag：

```bash
git ls-remote --tags origin v1.5.0
gh api repos/<owner>/<repo>/git/refs/tags/v1.5.0
```

5. **已发布的 tag 不得移动**。需要修正内容时发布新版本（例如 `1.5.1`），不得删除后重建同名 tag，也不得 `git push --force` 覆盖 tag。

## 步骤 6：创建 GitHub Release

1. 优先用用户环境中已登录的 CLI 创建 **GitHub Release**：

```bash
gh release create v1.5.0 --title "v1.5.0" --notes-file CHANGELOG-ENTRY.md
```

预发布版本：

```bash
gh release create v2.0.0-rc.1 --title "v2.0.0-rc.1" --prerelease --notes-file CHANGELOG-ENTRY.md
```

带附件时追加文件路径，或发布后用 `gh release upload v1.5.0 <文件>`。

2. CLI 不可用时给出网页端编号步骤，由用户完成：
   1. 打开仓库页面，进入 `Releases`。
   2. 选择 `Draft a new release`。
   3. 在 `Choose a tag` 中选择已推送的 tag，不要新建重复 tag。
   4. 填写标题与说明，说明内容来自 CHANGELOG 与 git 日志。
   5. 预发布版本勾选 `Set as a pre-release`。
   6. 点击 `Publish release`。
3. **release notes** 必须来自实际变更：`git log <上个tag>..<本次tag> --oneline` 与 diff 摘要。禁止编造功能、比较链接或下载量。
4. 附件与校验和：

```bash
gh release upload v1.5.0 dist/app-1.5.0.zip
sha256sum dist/app-1.5.0.zip
```

在说明中给出校验和时，数值必须来自本地实际计算结果。

## 步骤 7：发布后核验

1. 本地与远程逐项核验：

```bash
git ls-remote --tags origin v1.5.0
gh release view v1.5.0 --json tagName,isPrerelease,assets,url
gh api repos/<owner>/<repo>/releases/tags/v1.5.0 --jq '.tag_name, .prerelease'
```

2. 核验项与证据等级：

| 核验项 | 通过标准 | 证据等级 |
| --- | --- | --- |
| tag 指向正确提交 | 远程 tag 的对象哈希与预期提交一致 | L3 远程 API |
| Release 页面可访问 | 返回 200 且标题与版本号一致 | L3 远程 API |
| 预发布标记 | `prerelease` 字段与方案一致 | L3 远程 API |
| CI 结论 | 发布提交或标签工作流实际运行成功 | L4 CI |
| 附件可下载可用 | 下载后校验和匹配并能正常使用 | L5 发布物 |

3. **L5** 只能由实际下载使用得出；能看到附件条目不等于 L5。「本地已打 tag」不等于「远程已有该 tag」，也不等于「Release 已发布」。
4. 回报格式：当前阶段（发布，第 4/4 阶段）、版本号、tag 名、Release 链接、各核验项证据等级、唯一下一步（进入日常维护）。

## 回滚与纠错

1. **回滚**（版本回滚，把线上恢复到此前的稳定版本）：
   1. 停止发布动作，确认当前发布物与目标稳定版本。
   2. 不要移动或删除已发布 tag；改为发布新的修复版本，或在 Release 说明中标记该版本状态。
   3. 若必须撤回错误产物，按下面的纠错流程处理。
2. 发布内容纠错：

| 问题 | 正确做法 |
| --- | --- |
| Release 说明写错 | 直接编辑 Release 说明（不改变 tag），并在说明中注明修订 |
| 附件版本错误 | 替换附件前先说明；已下载的旧附件无法收回，必要时发布新版本 |
| tag 打错提交 | 未推送时删除本地 tag 重打；已推送且已发布时发布新版本 |
| 需要移除整个发布 | 属于危险操作，走单项授权，并说明已下载内容无法收回 |

3. 纠错后必须重新执行步骤 7 的核验，并更新项目状态文件。

## 门禁与危险操作边界

| 边界 | 规则 |
| --- | --- |
| 「发布方案确认」 | 未收到用户明确回复前，不创建 tag、不推送 tag、不创建 Release |
| 已发布的 tag 不得移动 | 不得删除后重建同名 tag，不得强制覆盖 tag |
| 删除 tag 或 Release | 危险操作，逐项单独说明影响并取得单项授权 |
| `force push` | 危险操作，禁止用于覆盖已发布历史 |
| 不得编造 | release notes、CHANGELOG 条目、校验和、日期都必须来自实际输出 |
| 版本号唯一来源 | 出现冲突时先列冲突再收敛，不得沉默地改其中一处 |
| 预发布 | 不稳定版本必须勾选 pre-release，不得伪装成稳定版 |
| 凭据红线 | 不把 token、密码、私钥写入 Release 说明或附件 |

## 相关文档

- 提交规范、分支策略与依赖更新：[maintenance.md](maintenance.md)
- 建仓与首推：[repo-setup-stage.md](repo-setup-stage.md)
- 验收用例：[acceptance-tests.md](acceptance-tests.md)
- 只读体检脚本：`../scripts/repo_doctor.py`
