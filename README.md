# 数字书库与漫画 Agent Skills

[![Tests](https://github.com/konghenfuxue-cpu/ai-skills/actions/workflows/tests.yml/badge.svg)](https://github.com/konghenfuxue-cpu/ai-skills/actions/workflows/tests.yml)
[![Latest release](https://img.shields.io/github/v/release/konghenfuxue-cpu/ai-skills)](https://github.com/konghenfuxue-cpu/ai-skills/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 这个项目有什么用

这是一个面向个人数字书库的公开 Agent Skills 工具集，让 Codex 按经过测试的流程处理漫画、电子书和 Calibre 书库，而不必在每次任务中重新说明工具、路径规则和安全要求。

它目前可以：

- 检查、合并、拆分和整理 CBZ，并维护 `ComicInfo.xml` 与可逆合并元数据；
- 从合并后的 CBZ 中删除指定子合集，同时保留剩余内容的拆分还原能力；
- 检查 EPUB 的 ZIP 包装、OPF、目录和章节引用，并安全修复可确定的问题；
- 将中文小说 TXT 按卷、章、完本感言和末尾番外转换为 EPUB 3，并生成封面、简介、制作说明与可点击分级目录；
- 只读审计 Calibre 书库，定位缺失格式、异常路径和重复候选；
- 润色中文文章、评论和文档，同时保留事实、确定程度和作者声音；
- 管理这些 Skill 的测试、GitHub 备份、安装、更新与恢复流程。
- 记录并复用私人纠错规则，减少同类失误反复出现。

项目强调本地处理、保留原文件、修改前确认和修改后验证。它不包含漫画或电子书文件，不绕过 DRM，也不会在没有任务请求时自动扫描书库。

当前工作流主要在 Windows 11、PowerShell 7 和 Python 3.11 环境验证。

## 先选你要完成的任务

| 你想做什么 | 从这里开始 |
| --- | --- |
| 检查、合并、拆分漫画 CBZ | [CBZ Workflow 使用说明](CBZ-Workflow使用说明.md) |
| 排查 EPUB 损坏或导入失败 | [EPUB Repair](skills/epub-repair/SKILL.md) |
| 把中文小说 TXT 制作为 EPUB | [TXT 转 EPUB 模板](skills/txt-to-epub-template/SKILL.md) |
| 查找 Calibre 书库缺失文件与重复候选 | [Calibre Workflow](skills/calibre-workflow/SKILL.md) |
| 润色中文文字 | [Humanizer-zh](skills/humanizer-zh/README.md) |

**第一次使用？** 先读 [从下载到第一次成功检查](新手入门.md)，从 ZIP 解压、Python 安装与独立环境开始，只检查一个文件副本。核心书库功能可直接运行 Python 脚本；需要让 Codex 按工作流执行时，再安装对应 Skill。它不是独立的图形界面书库软件，也不提供书籍资源。

仓库另附 Skill 仓库管理与私人纠错记忆工具，属于维护辅助功能；不必为了处理一本书安装全部技能。

当前公开稳定版：[`v1.1.0`](https://github.com/konghenfuxue-cpu/ai-skills/releases/tag/v1.1.0)。无需 GitHub 账号即可克隆或下载。

详细教程：

- [新手入门与常见问题](新手入门.md)
- [旧 v1.0.0 安装说明（历史）](公开版安装与使用教程.md)
- [CBZ Workflow 使用说明](CBZ-Workflow使用说明.md)
- [Skill 仓库管理使用说明](Skill仓库管理使用说明.md)
- [EPUB Repair 指南](skills/epub-repair/SKILL.md)
- [Calibre Workflow 指南](skills/calibre-workflow/SKILL.md)
- [Humanizer-zh 指南](skills/humanizer-zh/README.md)

参与和维护：

- [贡献指南](CONTRIBUTING.md)
- [安全策略](SECURITY.md)
- [社区行为准则](CODE_OF_CONDUCT.md)
- [变更日志](CHANGELOG.md)

## 安装前准备

- 使用 Windows 与 64 位 Python 3.11 或更高版本；新手下载 ZIP 不需要 Git。基础示例可用 Windows 自带 PowerShell，维护脚本另按各自要求准备 PowerShell 7。
- 先确认当前 Codex 的 Skill 发现目录。当前官方文档使用 `%USERPROFILE%\.agents\skills`，既有旧版安装可能使用 `.codex\skills`；不要在两处重复安装同名 Skill，详见新手教程。
- `cbz-workflow` 的基础 CBZ 功能只使用 Python 标准库；JMComic 下载功能额外需要 `jmcomic`、`Pillow` 和 `zhconv`。
- 运行前先把 Skill 中的本机路径配置改成自己的目录，并使用小型副本测试。

## 安装

按 [新手教程](新手入门.md) 下载 ZIP 并创建 `.venv`，先运行只读检查，再按需复制一个完整 Skill 目录。教程提供目标已存在时停止的安装命令，以及更新前备份与恢复步骤，避免直接覆盖旧安装。

`epub-repair` 和 `calibre-workflow` 只依赖 Python 标准库。JMComic 的额外固定依赖请按新手教程装到专用虚拟环境，基础 EPUB 检查不需要它们。

## 快速开始

双击 JMComic 下载入口时，工具会自动创建自身的 `.venv` 并安装同一份固定依赖；直接使用命令行时建议自行创建虚拟环境。直接依赖固定版本，传递依赖由 pip 解析。离线行为测试的运行方法见 [贡献指南](CONTRIBUTING.md)。

### 在 Codex 中使用

将目标文件或目录的准确路径告诉 Codex，并在请求中写出 Skill 名称即可。首次操作真实文件时，请使用副本。

```text
使用 $epub-repair 检查 "D:\\Books\\book.epub"，只报告问题，不要修改原文件。
```

```text
使用 $calibre-workflow 审计 "D:\\Calibre Library"，生成 JSON 报告；不要修改 metadata.db 或书籍文件。
```

```text
使用 $cbz-workflow 检查这个 CBZ 副本的页数与 ComicInfo.xml；先报告结果，不要覆盖原件。
```

```text
使用 $skill-repository-manager 检查我的源仓库、GitHub 和 Codex 安装副本是否同步。
```

```text
使用 $humanizer-zh 润色这篇中文文章，保留原有事实、语气和不确定程度。
```

```text
使用 $txt-to-epub-template，把中文小说 TXT 转成 EPUB；末尾连续番外建立可点击分组页。
```

```text
使用 $correction-memory 记住这次纠错；私人记录保存在我指定的本地文件，不上传到公开仓库。
```

### 直接运行只读检查

不使用 Codex 时，也可以在仓库根目录运行以下命令。示例均只读，不会覆盖或删除原文件。

```powershell
python '.\skills\epub-repair\scripts\epub_check_repair.py' 'D:\Books\book.epub'
python '.\skills\calibre-workflow\scripts\audit_calibre_library.py' 'D:\Calibre Library' --report '.\calibre-audit.json'
& '.\skills\skill-repository-manager\scripts\check-skill-repo.ps1'
```

EPUB 的 `--repair` 会创建新文件而非覆盖原文件；Calibre 审计以 SQLite 只读模式打开数据库。CBZ 的合并、拆分、元数据写入和删除子合集会修改或创建文件，请先阅读对应工具目录中的 `使用说明.txt`，并使用测试副本。

## 使用前提醒

- 这些脚本会处理本地文件；覆盖、删除或原地更新前请仔细确认目标。
- 仓库不包含漫画、电子书、JMComic 配置、Cookie、Token 或 API Key。
- 使用 JMComic 功能时，请自行确认当地法律、站点条款和内容授权。
- `cbz-workflow` 的本地核心流程已稳定；JMComic 网络下载属于外部依赖，仍需单独确认，详见各 Skill 的 `evals/`。

## 维护者本地配置

公开文档必须使用通用的占位符和说明，不包含维护者的用户名、电脑路径、邮箱或凭据。本地维护时，复制 `LOCAL.md.example` 为 `LOCAL.md`，并在其中记录路径和覆盖规则。`LOCAL.md` 已被 Git 忽略，任何 AI 在修改或发布前都应先读取它；提交前仍要确认暂存文件不包含本地个人化内容。

## 许可证

本项目以 [MIT License](LICENSE) 发布。你可以自由使用、复制、修改、分发和商用，但需在分发版本中保留版权声明与许可证文本。

## Skill 目录

| Skill | 状态 | 用途 | 最近测试 |
|---|---|---|---|
| cbz-workflow | 稳定（本地核心） | CBZ 合并、拆分、检测和元数据 | 2026-09-30 自动测试：流式元数据写入、重复条目保留、打包失败清理和完整性报告；此前有 ZIP64 验证 |
| skill-repository-manager | 稳定 | 创建、测试、备份、安装和更新个人 Skills | 2026-09-30 自动测试：安装副本 SHA256、缺失与多余文件、个人配置差异 |
| epub-repair | 稳定 | EPUB 包装、目录和结构检查与安全修复 | 2026-09-29 自动测试：新文件修复、原文件保持、OPF 歧义停止；此前有真实 EPUB 验证 |
| calibre-workflow | 稳定 | Calibre 书库只读审计、格式检查和重复候选识别 | 2026-09-29 自动测试：缺失文件、重复候选、数据库保持不变；此前有真实书库验证 |
| humanizer-zh | 稳定 | 中文文本润色与原意核对 | 2026-09-29 Skill 格式验证通过；18 个文本案例与文件结构样例见 Skill 内测试说明 |
| txt-to-epub-template | 稳定 | 中文小说 TXT 转 EPUB 3、分级目录与制作说明 | 2026-09-30 自动测试：番外目录和全部引用、GB18030 原稿、拒绝覆盖及失败清理；此前有真实 EPUB 验证 |
| correction-memory | 测试中 | 维护私人纠错记录并在后续相关任务中执行检查 | 2026-10-01 场景审查与 Skill 格式验证；私人记录不在仓库内 |

`humanizer-zh` 的正式维护位置是本仓库的 `skills/humanizer-zh/`；上游项目的独立克隆仅供对照更新，Codex 目录是安装副本。

## 状态说明

- 草稿：只有初步说明；
- 开发中：正在添加脚本；
- 测试中：已能使用，仍在验证；
- 稳定：通过真实任务测试；
- 已弃用：保留历史，不再使用。

## 仓库规则

- 每个正式 Skill 必须有独立文件夹；
- 入口文件必须命名为 `SKILL.md`；
- 脚本放入 `scripts/`；
- 参考资料放入 `references/`；
- 模板和静态资源放入 `assets/`；
- 测试案例放入 `evals/`；
- 不保存真实漫画、电子书、密码或 API 密钥。
