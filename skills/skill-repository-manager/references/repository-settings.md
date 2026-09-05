# 仓库与环境配置

## 公开仓库

- GitHub：`https://github.com/konghenfuxue-cpu/ai-skills`
- 默认分支：`main`
- 可见性：Public
- Skill 源目录：仓库根目录下的 `skills/`
- 旧版归档：仓库根目录下的 `archive/旧版脚本/`
- 测试记录：每个 Skill 内的 `evals/`

所有正式内容修改都在当前 Git 仓库中完成。具体克隆路径由使用者自行选择。

## Codex 安装位置

- Windows 默认用户 Skill 根目录：`%USERPROFILE%\.codex\skills`
- 单个 Skill 安装位置：`%USERPROFILE%\.codex\skills\<skill-name>`

安装副本只供 Codex 加载，不作为正式编辑位置。

## 本地覆盖

仓库根目录的 `LOCAL.md` 已被 Git 忽略，可用于记录维护者自己的克隆路径、Python 路径和安装目录。公开文件不得包含个人路径、邮箱或凭据。

## 当前已知 Skill

| Skill | 源目录 | 状态 |
|---|---|---|
| `cbz-workflow` | `skills/cbz-workflow` | 稳定（本地核心），已安装；2026-09-05 300 页与超过 2 GiB ZIP64 流式验证通过 |
| `skill-repository-manager` | `skills/skill-repository-manager` | 稳定，已安装；2026-09-05 多次真实提交、推送与安装同步通过 |
| `epub-repair` | `skills/epub-repair` | 稳定，已安装；2026-09-05 真实 EPUB 检查与临时副本修复通过 |
| `calibre-workflow` | `skills/calibre-workflow` | 稳定，已安装；2026-09-05 真实书库只读审计通过 |
