# Skill 仓库维护流程

## 新建 Skill

1. 明确 Skill 的单一职责、触发请求和不应触发的边界。
2. 在当前仓库的 `skills/<skill-name>` 创建 `SKILL.md`。
3. 只按实际需要添加 `scripts/`、`references/`、`assets/` 或 `evals/`。
4. 检查 YAML、相对链接、UTF-8 和目录命名。
5. 使用小型隔离样本测试，不直接使用唯一真实文件。
6. 将结果记录到 `evals/`，更新根目录 `README.md` 状态表。

## 更新现有 Skill

1. 阅读完整但精简的 `SKILL.md`；只按改动读取相关参考资料、脚本和调用位置，范围不确定时再扩大检查。
2. 识别本次会受影响的行为和已有测试。
3. 修改源仓库，不直接编辑 Codex 安装副本。
4. 保留与需求不冲突的旧功能。
5. 按改动风险选择验证：文档检查内容与链接，代码运行受影响的语法和行为测试。
6. 记录能帮助后续维护的结果、失败和限制。

## 验证

中文 Windows 上运行 Skill 验证器：

```powershell
$env:PYTHONUTF8='1'
$repo = (Get-Location).Path
python (Join-Path $env:USERPROFILE '.codex\skills\.system\skill-creator\scripts\quick_validate.py') `
  (Join-Path $repo 'skills\<skill-name>')
```

验证器通过不代表实际行为正确。脚本行为发生变化时使用隔离样本测试；纯文档修改无需重复无关业务测试。

## 提交和上传 GitHub

先执行只读检查：

```powershell
$repo = (Get-Location).Path
& (Join-Path $repo 'skills\skill-repository-manager\scripts\check-skill-repo.ps1')
git -C $repo diff --check
```

该检查会同时列出 Git 状态、远程地址、每个源 Skill 的入口文件，以及是否存在对应的 Codex 安装副本。需要查看更细的暂存内容时，再执行：

```powershell
git -C $repo status --short
git -C $repo diff --cached --stat
git -C $repo remote -v
```

确认没有凭据或大文件后提交，并先同步私有备份：

```powershell
git -C $repo add <明确的文件>
git -C $repo commit -m '简短说明'
git -C $repo push backup main
git -C $repo push backup --tags
```

私有备份成功后，审查公开远端尚未包含的全部提交与文件，而不只查看最后一次提交：

```powershell
git -C $repo log --oneline origin/main..HEAD
git -C $repo diff --name-status origin/main..HEAD
git -C $repo diff origin/main..HEAD
```

公开审查需确认没有维护者绝对路径、账号资料、本地配置、凭据、真实书籍或漫画以及不适合公开的日志和测试样本。通过后再执行：

```powershell
git -C $repo push origin main
git -C $repo push origin --tags
```

`LOCAL.md`、Obsidian 工作区和其他被 `.gitignore` 排除的内容不会进入私有 Git 备份。需要备份私有专属文件时，使用与公开 `main` 隔离的分支或备份方案；不要先把它们提交到将来会推送公开的历史中。

两个远端分别核验并报告；私有备份成功不代表公开发布审查已经通过。

不使用笼统提交来掩盖未检查文件。GitHub Desktop 中对应流程是：检查 Changes → 填写 Summary → Commit to main → Push origin。

## 安装到 Codex

个人 Skill 安装在：

```text
%USERPROFILE%\.codex\skills\<skill-name>
```

可通过 `$skill-installer` 从公开 GitHub 仓库安装。安装完成后运行标准验证，并检查随附脚本是否能加载依赖。

如果目标目录已存在，不直接覆盖。先比较源仓库、GitHub 和安装副本，确认需要更新后再采用可恢复的替换方式。

## 同步最新版

推荐顺序：

```text
Git 源仓库修改
→ 测试与验证
→ Git 提交
→ Push backup
→ 审查 origin/main..HEAD
→ Push origin
→ 更新 Codex 安装副本
→ 再次验证
```

不要反向把安装副本当成源文件同步回仓库，除非先确认其中确有尚未保存的用户修改。

## 恢复旧版本

1. 使用 `git log --oneline` 找到候选提交。
2. 使用 `git show <提交>:<文件路径>` 或 GitHub 历史查看内容。
3. 明确只恢复单个文件还是整个版本。
4. 优先创建新提交来恢复内容，保留完整历史。
5. 未获得明确授权时，不运行 `git reset --hard`、强制推送或递归删除。
