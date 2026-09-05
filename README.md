# Agent Skills

这个公开仓库收录可在 Codex 中使用的 Agent Skills、配套脚本、参考资料和测试记录。当前工作流主要在 Windows 11、PowerShell 7 和 Python 3.11 环境验证。

详细教程：

- [CBZ Workflow 使用说明](CBZ-Workflow使用说明.md)
- [Skill 仓库管理使用说明](Skill仓库管理使用说明.md)
- [EPUB Repair 指南](skills/epub-repair/SKILL.md)
- [Calibre Workflow 指南](skills/calibre-workflow/SKILL.md)

## 安装前准备

- 安装 [Git](https://git-scm.com/)、PowerShell 7 和 64 位 Python 3.11 或更高版本。
- 确认 Codex 用户 Skill 目录：Windows 默认为 `%USERPROFILE%\.codex\skills`。
- `cbz-workflow` 的基础 CBZ 功能只使用 Python 标准库；JMComic 下载功能额外需要 `jmcomic`、`Pillow` 和 `zhconv`。
- 运行前先把 Skill 中的本机路径配置改成自己的目录，并使用小型副本测试。

## 安装

```powershell
git clone https://github.com/konghenfuxue-cpu/ai-skills.git
Copy-Item -Recurse -Force '.\ai-skills\skills\cbz-workflow' "$env:USERPROFILE\.codex\skills\cbz-workflow"
Copy-Item -Recurse -Force '.\ai-skills\skills\epub-repair' "$env:USERPROFILE\.codex\skills\epub-repair"
Copy-Item -Recurse -Force '.\ai-skills\skills\calibre-workflow' "$env:USERPROFILE\.codex\skills\calibre-workflow"
Copy-Item -Recurse -Force '.\ai-skills\skills\skill-repository-manager' "$env:USERPROFILE\.codex\skills\skill-repository-manager"
```

安装后重启 Codex。若只需要一个 Skill，只复制对应子目录即可。`epub-repair` 和 `calibre-workflow` 只依赖 Python 标准库。安装 CBZ 中 JMComic 下载与打包功能的可选依赖：

```powershell
python -m pip install jmcomic Pillow zhconv
```

## 快速开始

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
- `cbz-workflow` 仍处于“测试中”，详见下方状态表和各 Skill 的 `evals/`。

## 维护者本地配置

公开文档必须使用通用的占位符和说明，不包含维护者的用户名、电脑路径、邮箱或凭据。本地维护时，复制 `LOCAL.md.example` 为 `LOCAL.md`，并在其中记录路径和覆盖规则。`LOCAL.md` 已被 Git 忽略，任何 AI 在修改或发布前都应先读取它；提交前仍要确认暂存文件不包含本地个人化内容。

## 许可证

本项目以 [MIT License](LICENSE) 发布。你可以自由使用、复制、修改、分发和商用，但需在分发版本中保留版权声明与许可证文本。

## Skill 目录

| Skill | 状态 | 用途 | 最近测试 |
|---|---|---|---|
| cbz-workflow | 测试中 | CBZ 合并、拆分、检测和元数据 | 2026-09-05 可逆删除边界与真实 CBZ 兼容修复通过 |
| skill-repository-manager | 稳定 | 创建、测试、备份、安装和更新个人 Skills | 2026-09-05 多次真实提交、推送与安装同步通过 |
| epub-repair | 稳定 | EPUB 包装、目录和结构检查与安全修复 | 2026-09-05 真实 EPUB 检查与临时副本修复通过 |
| calibre-workflow | 稳定 | Calibre 书库只读审计、格式检查和重复候选识别 | 2026-09-05 真实书库只读审计通过 |

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
