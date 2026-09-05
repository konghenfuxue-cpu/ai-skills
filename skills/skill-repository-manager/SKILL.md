---
name: skill-repository-manager
description: 管理用户的个人 Agent Skills 源仓库，包括创建或更新 Skill、检查目录与安全性、记录测试、提交并推送 GitHub 仓库，以及同步 Codex 安装副本。当用户询问 Skill 放在哪里、如何备份、上传 GitHub、安装、更新、同步或恢复时使用。不用于执行 CBZ、EPUB 等业务 Skill 本身的任务。
---

# 个人 Skill 仓库管理

维护用户唯一的 Agent Skills 源仓库，并在 Obsidian、GitHub 和 Codex 安装目录之间执行可验证的发布流程。

开始任务时读取[仓库与环境配置](references/repository-settings.md)。需要创建、更新、提交、安装或恢复时，再读取[维护流程](references/maintenance-workflow.md)。

## 核心原则

1. `D:\ai-skill\skill` 是唯一源仓库；正式修改只在这里完成。
2. `C:\Users\lv\.codex\skills` 中的个人 Skill 是安装副本，不在其中手工维护。
3. GitHub 公开仓库用于版本历史、备份与分享，不存放真实漫画、电子书、密钥、Cookie、账号凭据或大文件。
4. 每个 Skill 使用独立文件夹，入口必须准确命名为 `SKILL.md`。
5. 新建或重大修改后先验证，再提交、推送和安装。
6. 不删除旧脚本；先比较功能，无法确定时移入 `archive/旧版脚本/`。
7. 提交、推送、覆盖安装副本、删除或恢复版本前，先报告将要改变的目标并取得用户确认。

## 根据请求选择动作

- “Skill 放在哪里/仓库是什么”：读取并回答 `repository-settings.md`。
- “检查仓库/现在是否同步”：运行 `scripts/check-skill-repo.ps1`，报告本地状态、远程地址和安装情况。
- “创建新 Skill”：使用 `$skill-creator`，在源仓库 `skills/<skill-name>/` 创建并验证。
- “更新现有 Skill”：只修改源仓库，保留旧功能并更新测试记录。
- “上传 GitHub”：先检查 `.gitignore` 和待提交文件，再提交并推送 `main`。
- “安装到 Codex”：从私有 GitHub 仓库或已验证源目录安装到用户 Skill 目录。
- “同步最新版”：确认源仓库已提交和推送，再更新安装副本并重新验证。
- “恢复旧版本”：先显示目标提交和受影响文件，不直接执行破坏性恢复。

## 创建或更新 Skill 的最低要求

- 文件夹名、YAML `name` 使用小写字母、数字和短横线。
- `SKILL.md` 包含准确、可区分的 `name` 和 `description`。
- 核心决策放在 `SKILL.md`，详细说明放在 `references/`。
- 只有重复、确定性的操作才添加 `scripts/`。
- 真实测试或错误记录放入 `evals/`。
- 使用 UTF-8；在中文 Windows 上运行验证器时启用 Python UTF-8 模式。

## 安全检查

提交前检查：

1. `git status` 中没有 `*.cbz`、`*.epub`、`*.pdf`、压缩包、日志或密钥。
2. `.env`、`*.key`、Cookie、令牌和账号凭据没有进入暂存区。
3. `SKILL.md` 中的本地路径是用户明确允许保存的配置。
4. 脚本没有来源不明的下载执行命令。
5. GitHub 远程仍指向预期的 `ai-skills` 仓库。

## 完成报告

每次维护结束报告：

- 修改或新增的 Skill；
- 源仓库文件位置；
- 验证与测试结果；
- Git 提交号和远程同步状态；
- Codex 安装位置和版本状态；
- 尚未完成或需要人工确认的事项。
