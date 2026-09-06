---
name: skill-repository-manager
description: 创建、更新、验证、发布和同步个人 Codex Skills；用于管理 Skill 源仓库、GitHub 版本和 Codex 安装副本。
---

# 个人 Skill 仓库管理

维护 Agent Skills 源仓库，并在本地工作区、GitHub 和 Codex 安装目录之间执行可验证的发布流程。

开始任务时读取[仓库与环境配置](references/repository-settings.md)。需要创建、更新、提交、安装或恢复时，再读取[维护流程](references/maintenance-workflow.md)。

## 核心原则

1. 当前 Git 仓库是唯一源仓库；正式修改只在这里完成。
2. `%USERPROFILE%\.codex\skills` 中的个人 Skill 是安装副本，不在其中手工维护。
3. GitHub 公开仓库用于版本历史与分享；可配置名为 `backup` 的私有远端保存同一份 Git 历史。两个远端都不存放真实漫画、电子书、密钥、Cookie、账号凭据或大文件。
4. 每个 Skill 使用独立文件夹，入口必须准确命名为 `SKILL.md`。
5. 新建或行为修改后运行与改动相称的验证，再提交、推送和安装。
6. 不删除旧脚本；先比较功能，无法确定时移入 `archive/旧版脚本/`。
7. 执行外部发布、覆盖安装副本、删除或恢复前需要用户授权；同一任务中已经给出的授权持续有效，范围或目标实质变化时再询问。

## 根据请求选择动作

- “Skill 放在哪里/仓库是什么”：读取并回答 `repository-settings.md`。
- “检查仓库/现在是否同步”：运行 `scripts/check-skill-repo.ps1`，报告本地状态、远程地址和安装情况。
- “创建新 Skill”：使用 `$skill-creator`，在源仓库的 `skills/<skill-name>/` 创建并验证。
- “更新现有 Skill”：只修改源仓库，保留旧功能并更新测试记录。
- “上传 GitHub”：先检查 `.gitignore` 和待提交文件，再提交并推送 `origin`；存在 `backup` 远端时一并同步分支和标签。
- “安装到 Codex”：从公开 GitHub 仓库或已验证源目录安装到用户 Skill 目录。
- “同步最新版”：确认源仓库已提交和推送，再更新安装副本并重新验证。
- “恢复旧版本”：先显示目标提交和受影响文件，不直接执行破坏性恢复。

## 创建或更新 Skill 的最低要求

- 文件夹名、YAML `name` 使用小写字母、数字和短横线。
- `SKILL.md` 包含准确、可区分的 `name` 和 `description`。
- 核心决策放在 `SKILL.md`，详细说明放在 `references/`。
- 只有重复、确定性的操作才添加 `scripts/`。
- 对后续维护有价值的真实测试或错误记录放入 `evals/`。
- 使用 UTF-8；在中文 Windows 上运行验证器时启用 Python UTF-8 模式。

## 安全检查

提交前检查：

1. `git status` 中没有 `*.cbz`、`*.epub`、`*.pdf`、压缩包、日志或密钥。
2. `.env`、`*.key`、Cookie、令牌和账号凭据没有进入暂存区。
3. `SKILL.md` 中的本地路径是用户明确允许保存的配置。
4. 脚本没有来源不明的下载执行命令。
5. GitHub 远程仍指向预期的 `ai-skills` 仓库。

## 完成报告

报告本次实际发生的修改、验证结果和同步状态；只列出与任务有关的未完成事项。
