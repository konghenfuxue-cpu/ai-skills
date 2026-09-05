# Agent Skills

这个公开仓库收录可在 Codex 中使用的 Agent Skills、配套脚本、参考资料和测试记录。当前工作流主要在 Windows 11、PowerShell 7 和 Python 3.11 环境验证。

日常使用方法请查看：[CBZ Workflow 使用说明](CBZ-Workflow使用说明.md)。

Skill 创建、备份、安装和同步方法请查看：[Skill 仓库管理使用说明](Skill仓库管理使用说明.md)。

## 安装前准备

- 安装 [Git](https://git-scm.com/)、PowerShell 7 和 64 位 Python 3.11 或更高版本。
- 确认 Codex 用户 Skill 目录：Windows 默认为 `%USERPROFILE%\.codex\skills`。
- `cbz-workflow` 的基础 CBZ 功能只使用 Python 标准库；JMComic 下载功能额外需要 `jmcomic`、`Pillow` 和 `zhconv`。
- 运行前先把 Skill 中的本机路径配置改成自己的目录，并使用小型副本测试。

## 安装

```powershell
git clone https://github.com/konghenfuxue-cpu/ai-skills.git
Copy-Item -Recurse -Force '.\ai-skills\skills\cbz-workflow' "$env:USERPROFILE\.codex\skills\cbz-workflow"
Copy-Item -Recurse -Force '.\ai-skills\skills\skill-repository-manager' "$env:USERPROFILE\.codex\skills\skill-repository-manager"
```

安装后重启 Codex。如果只需要某一个 Skill，只复制对应子目录即可。安装 JMComic 可选依赖：

```powershell
python -m pip install jmcomic Pillow zhconv
```

## 使用前提醒

- 这些脚本会处理本地文件；覆盖、删除或原地更新前请仔细确认目标。
- 仓库不包含漫画、电子书、JMComic 配置、Cookie、Token 或 API Key。
- 使用 JMComic 功能时，请自行确认当地法律、站点条款和内容授权。
- 部分功能仍处于“测试中”，详见下方状态表和各 Skill 的 `evals/`。

## 维护者本地配置

公开文档必须使用通用的占位符和说明，不包含维护者的用户名、电脑路径、邮箱或凭据。本地维护时，复制 `LOCAL.md.example` 为 `LOCAL.md`，并在其中记录路径和覆盖规则。`LOCAL.md` 已被 Git 忽略，任何 AI 在修改或发布前都应先读取它；提交前仍要确认暂存文件不包含本地个人化内容。

## Skill 目录

| Skill | 状态 | 用途 | 最近测试 |
|---|---|---|---|
| cbz-workflow | 测试中 | CBZ 合并、拆分、检测和元数据 | 2026-09-03 本地核心流程测试通过 |
| skill-repository-manager | 测试中 | 创建、测试、备份、安装和更新个人 Skills | 2026-09-03 新建 |
| epub-repair | 计划中 | EPUB 目录和结构修复 | 尚未创建 |
| calibre-workflow | 计划中 | Calibre 书库整理 | 尚未创建 |

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
