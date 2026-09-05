# Skill 仓库维护流程

## 新建 Skill

1. 明确 Skill 的单一职责、触发请求和不应触发的边界。
2. 在 `D:\ai-skill\skill\skills\<skill-name>` 创建 `SKILL.md`。
3. 只按实际需要添加 `scripts/`、`references/`、`assets/` 或 `evals/`。
4. 检查 YAML、相对链接、UTF-8 和目录命名。
5. 使用小型隔离样本测试，不直接使用唯一真实文件。
6. 将结果记录到 `evals/`，更新根目录 `README.md` 状态表。

## 更新现有 Skill

1. 阅读完整 `SKILL.md`、相关参考资料、脚本和说明。
2. 盘点现有功能和测试状态。
3. 修改源仓库，不直接编辑 Codex 安装副本。
4. 保留与需求不冲突的旧功能。
5. 先做语法或格式验证，再做行为测试。
6. 记录修改内容、通过项、失败项和限制。

## 验证

中文 Windows 上运行 Skill 验证器：

```powershell
$env:PYTHONUTF8='1'
& 'C:\Users\lv\AppData\Local\Programs\Python\Python311\python.exe' `
  'C:\Users\lv\.codex\skills\.system\skill-creator\scripts\quick_validate.py' `
  'D:\ai-skill\skill\skills\<skill-name>'
```

验证器通过不代表实际行为正确；有脚本时还需要隔离测试。

## 提交和上传 GitHub

先执行只读检查：

```powershell
git -C 'D:\ai-skill\skill' status --short
git -C 'D:\ai-skill\skill' diff --check
git -C 'D:\ai-skill\skill' remote -v
```

确认没有敏感或大文件后：

```powershell
git -C 'D:\ai-skill\skill' add <明确的文件>
git -C 'D:\ai-skill\skill' commit -m '简短说明'
git -C 'D:\ai-skill\skill' push origin main
```

不使用笼统提交来掩盖未检查文件。GitHub Desktop 中对应流程是：检查 Changes → 填写 Summary → Commit to main → Push origin。

## 安装到 Codex

个人 Skill 安装在：

```text
C:\Users\lv\.codex\skills\<skill-name>
```

可通过 `$skill-installer` 从私有 GitHub 仓库安装。安装完成后运行标准验证，并检查随附脚本是否能加载依赖。

如果目标目录已存在，不直接覆盖。先比较源仓库、GitHub 和安装副本，确认需要更新后再采用可恢复的替换方式。

## 同步最新版

推荐顺序：

```text
Obsidian 源仓库修改
→ 测试与验证
→ Git 提交
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
