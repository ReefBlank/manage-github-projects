# 在 DeepSeek Harness（DSH）中安装为 Agent 预设

DSH 有两处用户级目录：

| 用途 | 路径 | 入口 |
| --- | --- | --- |
| 用户级 Skill | `~/.dsh/skills/` | `~/.dsh/skills/manage-github-projects/SKILL.md` |
| Agent 预设 | `~/.dsh/.agent-presets/` | `~/.dsh/.agent-presets/manage-github-projects/agent.cordis.yml` |

预设目录的结构是一个完整的 agent-plane 组合：

```text
~/.dsh/.agent-presets/manage-github-projects/
├── preset.yml            # 界面元数据：name / description / order
├── agent.cordis.yml      # 工具行、persona、skill 目录挂载
└── skills/
    └── manage-github-projects/
        └── SKILL.md      # 预设自带的 Skill
```

`agent.cordis.yml` 中的 `skill-filesystem` 行会把预设自身的 `skills/` 目录注册为 skill 根，
因此预设自带 Skill，不依赖部署级配置。

## 一键安装

在仓库根目录运行：

```powershell
python scripts/install_dsh_preset.py
```

脚本会：

1. 把仓库根目录复制到 `~/.dsh/skills/manage-github-projects`（入口 `SKILL.md`）；
2. 在 `~/.dsh/.agent-presets/manage-github-projects` 写入 `preset.yml` 与 `agent.cordis.yml`；
3. 把 Skill 复制到该预设的 `skills/manage-github-projects/`；
4. 打印真实安装路径与校验命令。

已存在同名安装时脚本会拒绝覆盖并提示先核对版本与来源；确认要替换时加 `--force`。

只想装 Skill、不建预设：

```powershell
python scripts/install_dsh_preset.py --skip-preset
```

自定义目录（例如 portable 环境）：

```powershell
python scripts/install_dsh_preset.py --skills-dir D:\dsh\skills --presets-dir D:\dsh\.agent-presets
```

## 手工安装

```powershell
git clone https://github.com/ReefBlank/manage-github-projects "$env:USERPROFILE\.dsh\skills\manage-github-projects"

$preset = "$env:USERPROFILE\.dsh\.agent-presets\manage-github-projects"
New-Item -ItemType Directory -Force -Path "$preset\skills" | Out-Null
Copy-Item -Recurse -Force "$env:USERPROFILE\.dsh\skills\manage-github-projects" "$preset\skills\"
Copy-Item -Force .\preset\preset.yml, .\preset\agent.cordis.yml $preset
```

## 启用

安装后重启或刷新 DSH Host，新建会话时在预设列表中选择「GitHub 项目管理助手」。
预设会把 `manage-github-projects` Skill 挂到该 Agent 的 skill 目录层，因此也可以在该会话里用 skill 工具显式加载。

若预设列表没有出现，按顺序检查：

1. `~/.dsh/.agent-presets/manage-github-projects/preset.yml` 是否存在且能解析；
2. `agent.cordis.yml` 与 `skills/manage-github-projects/SKILL.md` 是否都在；
3. DSH 日志中是否有该预设的挂载错误（通常是某个 `@deepseek-ai/*` 行在当前版本不存在）。

第 3 种情况说明该预设依赖的某个工具包在本机 DSH 版本中不可用，需要按日志逐行调整 `agent.cordis.yml`，
而不是删除整个预设。

## 卸载

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.dsh\.agent-presets\manage-github-projects"
Remove-Item -Recurse -Force "$env:USERPROFILE\.dsh\skills\manage-github-projects"
```
