# 贡献指南

感谢你考虑为本项目贡献。

## 提交前

```powershell
python scripts/validate_skill.py .
python -m unittest discover -s tests -v
python scripts/repo_doctor.py .
```

`repo_doctor.py` 出现阻塞项时不要提交。

## 变更约定

- 提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)：`feat:`、`fix:`、`docs:`、`test:`、`chore:` 等。
- 修改行为时同步更新 `references/` 中对应的手册；修改结构时同步更新 `scripts/validate_skill.py` 的 `REQUIRED_FILES` 与 `REQUIRED_PHRASES`。
- 新增脚本必须带 `#!/usr/bin/env python3` shebang、`argparse` 帮助文本，并且默认只读。
- 任何脚本都不得读取、回显或写出用户的凭据，也不得执行未经门禁授权的破坏性操作。

## 新增引用文档

1. 在 `references/` 下新建 Markdown 文件，使用单个 `# ` 一级标题。
2. 在 `SKILL.md` 中链接该文件，并说明它属于哪个阶段。
3. 在 `scripts/validate_skill.py` 的 `REQUIRED_FILES`（以及在需要时 `CONTENT_ASSERTIONS`）中登记。
4. 在 `references/acceptance-tests.md` 中补充覆盖该文档的用例。

## Pull Request

- 一个 PR 只做一件事，描述里写清动机、改动范围和验证方式。
- 引用外部资料时保留出处与许可证，不要整段复制第三方文本。
- 不要在本仓库中提交真实凭据、真实用户数据或大体积二进制文件。

## 许可证

贡献即表示你同意以本项目的 [MIT License](LICENSE) 发布你的贡献。
