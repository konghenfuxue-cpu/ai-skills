# Skill 仓库管理使用说明

## 1. 这是什么

`skill-repository-manager` 是你的个人 Agent Skills 管理 Skill。

它不负责合并 CBZ、修复 EPUB 等具体业务，而是管理这些业务 Skill 的完整生命周期：

```text
创建或修改
→ 测试与验证
→ 保存到 Obsidian 源仓库
→ 提交并推送 GitHub
→ 安装或更新到 Codex
→ 检查同步状态
→ 必要时恢复旧版本
```

你可以把它理解为“Skill 管家”。

## 2. 三个位置的分工

### Obsidian：唯一源文件

```text
D:\ai-skill\skill
```

用途：

- 正式编辑 Skill；
- 保存脚本、参考资料和测试记录；
- 用 Obsidian 浏览和检索；
- 作为本地 Git 仓库。

所有正式修改都从这里开始。

### GitHub：历史与远程备份

```text
https://github.com/konghenfuxue-cpu/ai-skills
```

配置：

- 仓库：`ai-skills`
- 所有者：`konghenfuxue-cpu`
- 可见性：Public
- 默认分支：`main`
- 远程名称：`origin`

用途：保存提交历史、比较变化、跨电脑备份和恢复旧版本。

### Codex：安装与执行副本

```text
%USERPROFILE%\.codex\skills
```

用途：让 Codex 发现和调用个人 Skill。

这里的文件是安装副本，不是正式编辑位置。不要在 Codex 安装目录和 Obsidian 源仓库中分别维护两个版本。

## 3. 如何调用

Codex 可以根据请求自动选择这个 Skill。也可以明确写：

```text
使用 $skill-repository-manager 检查我的 Skill 仓库是否同步。
```

### 常用请求

查询位置：

```text
使用 $skill-repository-manager 告诉我 Skill 源文件、GitHub 仓库和 Codex 安装副本分别在哪里。
```

检查状态：

```text
使用 $skill-repository-manager 检查本地仓库、GitHub 和 Codex 安装副本是否同步。
```

创建新 Skill：

```text
使用 $skill-repository-manager 创建一个 epub-repair Skill，先测试，再上传 GitHub 并安装到 Codex。
```

更新现有 Skill：

```text
使用 $skill-repository-manager 更新 cbz-workflow，保留旧功能，验证后提交并同步安装副本。
```

检查安全性：

```text
使用 $skill-repository-manager 检查待提交内容，确认没有漫画、电子书、日志、密码或密钥。
```

恢复版本：

```text
使用 $skill-repository-manager 查看这个 Skill 的历史版本。先显示差异，不要直接恢复。
```

## 4. 源仓库结构

```text
D:\ai-skill\skill\
├── README.md
├── .gitignore
├── skills\
│   ├── cbz-workflow\
│   └── skill-repository-manager\
├── archive\
│   └── 旧版脚本\
└── .obsidian\
```

单个 Skill 的推荐结构：

```text
skill-name\
├── SKILL.md
├── scripts\       # 可选：确定性的重复操作
├── references\    # 可选：详细配置和规范
├── assets\        # 可选：输出模板和静态资源
└── evals\         # 可选：测试请求和测试结果
```

入口文件必须准确命名为 `SKILL.md`。

## 5. 新建 Skill 的标准流程

1. 明确 Skill 的单一职责。
2. 列出应该触发和不应该触发的请求。
3. 在 `D:\ai-skill\skill\skills\<skill-name>` 创建文件夹。
4. 创建 `SKILL.md`，填写 YAML `name` 和 `description`。
5. 只在确有需要时添加 `scripts/`、`references/`、`assets/` 或 `evals/`。
6. 运行标准格式验证。
7. 使用隔离样本做行为测试。
8. 记录测试结果并更新根目录 `README.md`。
9. 检查待提交文件安全性。
10. 提交并推送 GitHub。
11. 安装到 Codex 并再次验证。

Skill 文件夹名和 YAML `name` 应使用小写字母、数字和短横线，例如：

```text
epub-repair
calibre-workflow
skill-repository-manager
```

## 6. 修改现有 Skill

1. 读取完整 `SKILL.md` 和相关参考资料。
2. 阅读脚本与使用说明，盘点现有功能。
3. 明确本次新增或修复内容。
4. 只修改 Obsidian 源仓库。
5. 保留与新要求不冲突的旧功能。
6. 做语法、格式和行为测试。
7. 更新 `evals/` 中的测试记录。
8. 提交、推送并更新 Codex 安装副本。

如果出现多个旧脚本，不要直接删除。先比较功能，无法确定时保存到：

```text
D:\ai-skill\skill\archive\旧版脚本
```

## 7. 标准验证

当前 Python：

```text
Python 3.11.9 64 位
python
```

中文 Windows 上验证 Skill：

```powershell
$env:PYTHONUTF8='1'
& python `
  "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" `
  'D:\ai-skill\skill\skills\skill-name'
```

出现以下内容代表基础结构通过：

```text
Skill is valid!
```

注意：格式通过不等于功能一定正确。有脚本的 Skill 仍需使用隔离样本测试。

## 8. 一键健康检查

本 Skill 附带只读脚本：

```text
D:\ai-skill\skill\skills\skill-repository-manager\scripts\check-skill-repo.ps1
```

运行：

```powershell
& 'D:\ai-skill\skill\skills\skill-repository-manager\scripts\check-skill-repo.ps1'
```

它会显示：

- Git 当前分支和未提交修改；
- GitHub 远程地址；
- 源仓库中的 Skill；
- 每个 Skill 是否包含 `SKILL.md`；
- 每个 Skill 是否已经安装到 Codex。

它只读取状态，不会提交、推送、覆盖或删除文件。

## 9. 上传 GitHub

### 使用 GitHub Desktop

1. 打开 GitHub Desktop。
2. 确认当前仓库为 `ai-skills`。
3. 检查左侧 Changes。
4. 确认没有漫画、电子书、日志、压缩包或密钥。
5. 在 Summary 中填写修改说明。
6. 点击 `Commit to main`。
7. 点击顶部 `Push origin`。

常见按钮：

- `0 changed files`：没有新修改。
- `Commit to main`：把本地修改记入版本历史。
- `Push origin`：把本地提交上传 GitHub。
- `Fetch origin`：检查远程是否有更新。
- `Pull origin`：下载远程的新提交。

### 使用命令行

先检查：

```powershell
git -C 'D:\ai-skill\skill' status --short
git -C 'D:\ai-skill\skill' diff --check
git -C 'D:\ai-skill\skill' remote -v
```

确认后再提交明确文件：

```powershell
git -C 'D:\ai-skill\skill' add <文件或目录>
git -C 'D:\ai-skill\skill' commit -m '简短修改说明'
git -C 'D:\ai-skill\skill' push origin main
```

## 10. 安装或更新到 Codex

安装位置：

```text
%USERPROFILE%\.codex\skills\<skill-name>
```

推荐顺序：

```text
Obsidian 修改
→ 测试
→ Git 提交
→ Push origin
→ 安装或更新 Codex 副本
→ 再次验证
```

如果 Codex 没有显示新 Skill：

1. 检查安装目录中是否存在 `SKILL.md`。
2. 检查 YAML `name` 和 `description`。
3. 重新启动 Codex。

如果安装目标已存在，不要盲目覆盖。先比较源仓库、GitHub 和安装副本的差异。

## 11. 安全检查清单

提交前确认：

- [ ] 没有 `*.cbz`、`*.cbr`、`*.epub`、`*.pdf`、`*.zip` 或 `*.rar`；
- [ ] 没有 `.env`、`*.key`、Cookie、Token 或 API Key；
- [ ] 没有下载日志、临时输出或 Python 缓存；
- [ ] `.gitignore` 仍然生效；
- [ ] GitHub 远程仍指向预期的 `ai-skills`；
- [ ] 新脚本没有来源不明的下载执行命令；
- [ ] 本地路径和账号信息属于允许保存的配置；
- [ ] 删除、覆盖和恢复操作已经确认准确目标。

## 12. 恢复旧版本

安全流程：

1. 查看提交历史。
2. 选择候选提交。
3. 查看文件差异。
4. 明确恢复单个文件还是一组文件。
5. 优先用一个新的提交保存恢复结果。

未明确确认时，不使用：

```text
git reset --hard
git push --force
递归删除整个 Skill 文件夹
```

可以直接向 Codex 说：

```text
使用 $skill-repository-manager 查看 cbz-workflow 的历史版本，先比较差异，不要修改文件。
```

## 13. 当前状态

| 项目 | 状态 |
|---|---|
| Obsidian 源仓库 | 正常 |
| GitHub 公开仓库 | 已连接 |
| 默认分支 | `main` |
| `cbz-workflow` | 已保存、已上传、已安装 |
| `skill-repository-manager` | 已保存、已上传、已安装 |
| 仓库健康检查脚本 | 已验证 |

## 14. 最重要的规则

只记住一条也可以：

> 正式修改永远回到 `D:\ai-skill\skill`，测试通过后上传 GitHub，最后再更新 `%USERPROFILE%\.codex\skills` 中的安装副本。
