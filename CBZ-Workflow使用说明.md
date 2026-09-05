# CBZ Workflow 使用说明

## 1. 这是什么

`cbz-workflow` 是一个供 Codex 使用的个人 CBZ 漫画处理 Skill。

它把你的处理规则、本机环境、测试记录和现有脚本集中到一个位置，使 Codex 在遇到 CBZ 任务时能够：

- 识别应该使用哪一组工具；
- 保留已有标题、作者、系列和简介；
- 先用副本测试，再处理真实文件；
- 处理中文、日文、空格和特殊字符路径；
- 对修改后的 ZIP、图片页数和 `ComicInfo.xml` 做验证；
- 避免每次新对话都重新说明规则和目录。

它不会在后台自动扫描或修改漫画。只有你提出 CBZ 相关请求时，Codex 才会读取并使用它。

## 2. 主要位置

| 用途 | 位置 |
|---|---|
| Obsidian 源仓库 | `D:\ai-skill\skill` |
| Skill 源文件 | `D:\ai-skill\skill\skills\cbz-workflow` |
| Codex 安装副本 | `%USERPROFILE%\.codex\skills\cbz-workflow` |
| GitHub 公开仓库 | `https://github.com/konghenfuxue-cpu/ai-skills` |

重要原则：正式修改始终在 Obsidian 源仓库完成，不要直接编辑 Codex 安装副本。

## 3. 如何调用

Codex 可以根据请求内容自动选择这个 Skill。为了明确指定，也可以在任务中写：

```text
使用 $cbz-workflow 检查这个 CBZ 副本的页数和 ComicInfo.xml，不要修改原文件。
```

### 常用请求示例

检查页数和元数据：

```text
使用 $cbz-workflow 检查这批 CBZ 的实际图片页数，保留原元数据，先报告准备修改的文件。
```

写入作者和页数：

```text
使用 $cbz-workflow 给这些 CBZ 写入作者和页数。第一次先用一个副本测试。
```

合并章节：

```text
使用 $cbz-workflow 按自然顺序合并这些 CBZ，把原文件名记录到简介，默认保留原文件。
```

拆分合集：

```text
使用 $cbz-workflow 检查这个可逆合集，并拆分还原到新文件夹，不覆盖现有文件。
```

删除子合集：

```text
使用 $cbz-workflow 分析这个大合集中的第 16 个子合集。先显示名称、范围和页数，等我确认后再删除。
```

检查下载完整性：

```text
使用 $cbz-workflow 扫描 JMComic 分卷报告，列出缺失或损坏的作品，并生成可复制的 JM 号清单。
```

修复脚本：

```text
使用 $cbz-workflow 检查这个脚本为什么处理不了大于 2 GB 的 CBZ。先列出现有功能，不要丢失旧功能。
```

## 4. 工具目录

| 目录 | 用途 |
|---|---|
| `scripts/pagecount-metadata/` | 统计页数，写入 `ComicInfo.xml` 和 Calibre 元数据 |
| `scripts/reversible-merge-split/` | 可逆合并和拆分还原 CBZ |
| `scripts/remove-subcollection/` | 删除指定数字分组并重新编号 |
| `scripts/jm-report-check/` | 检查 JMComic 分卷报告完整性 |
| `scripts/jmcomic-download-pack/` | 本地扫描、章节分类、打包和下载衔接 |
| `references/` | 本机路径、软件版本和用户偏好 |
| `evals/` | 测试请求和实际测试结果 |

每组脚本旁边都有 `使用说明.txt`。执行前应先阅读对应说明。

## 5. 已验证功能

截至 2026-09-03，以下项目已经通过隔离测试或真实文件副本测试：

- 8 个 Python 脚本语法检查；
- 页数识别与 `PageCount` 写入；
- 标题、作者、系列、简介和其他 XML 字段保留；
- 可逆合并与自然排序；
- 按清单拆分并逐项还原；
- 删除指定子合集并重新编号；
- JM 分卷报告的完整、缺失和损坏识别；
- 重复 JM 号去重和续传列表生成；
- 简繁重复目录选择更完整版本；
- 正文和公告分类；
- 本地图片转 CBZ；
- 作者、页数和 ZIP 完整性验证；
- 真实 CBZ 副本测试，原文件 SHA-256 保持不变。

尚未完成的高负载或外部测试：

- 超过 2 GB 的真实 CBZ；
- 数百或数千页的大合集；
- JMComic API 搜索和实际网络下载。

这些场景执行前仍应使用副本，并明确确认网络或覆盖操作。

## 6. 安全规则

1. 第一次运行新脚本时只使用测试副本。
2. 不把真实漫画、电子书、日志、密码、Cookie 或 API Key 放入 Skill 仓库。
3. 覆盖、删除原文件或删除子合集前，必须确认准确目标。
4. 默认保留原始 CBZ；需要原地更新时，先确认文件未被 Calibre 或阅读器占用。
5. 验证失败时，不把结果报告为成功，也不继续覆盖原件。
6. 大文件应使用流式处理或临时 ZIP 重建，避免一次性读入内存。
7. 操作后检查 ZIP 结构、XML、图片数量、排序和临时文件。

## 7. 日常修改与同步

### 修改源文件

1. 在 Obsidian 中打开 `D:\ai-skill\skill`。
2. 修改 `skills/cbz-workflow` 中的说明或脚本。
3. 使用小型副本测试修改结果。
4. 在 `evals/` 中记录重要测试。

### 提交到 GitHub

1. 打开 GitHub Desktop。
2. 确认当前仓库是 `ai-skills`。
3. 检查变更列表中没有 CBZ、EPUB、PDF、日志或密钥。
4. 在左下角填写简短修改说明。
5. 点击 `Commit to main`。
6. 点击顶部的 `Push origin`。

### 更新 Codex 安装副本

GitHub 中的源仓库更新后，需要重新同步或安装 `cbz-workflow`，Codex 才会使用新版本。

不要在以下两个位置分别手工修改同一个文件：

```text
D:\ai-skill\skill\skills\cbz-workflow
%USERPROFILE%\.codex\skills\cbz-workflow
```

前者是唯一源文件位置；后者只是 Codex 加载用的安装副本。

## 8. Python 环境

当前已确认环境：

```text
Python 3.11.9 64 位
python
```

JMComic 本地打包相关依赖已经确认：

```text
jmcomic 2.7.4
Pillow 12.3.0
zhconv
```

检查 Python：

```powershell
python --version
python -c "import sys; print(sys.executable); print(sys.maxsize > 2**32)"
```

最后一项显示 `True` 表示使用 64 位 Python。

## 9. 故障排查

### Codex 没有调用 Skill

在请求中明确写：

```text
使用 $cbz-workflow 完成这个任务。
```

若仍未出现，重新启动 Codex，检查下面的文件是否存在：

```text
%USERPROFILE%\.codex\skills\cbz-workflow\SKILL.md
```

### CMD 提示找不到 Python

关闭并重新打开 PowerShell 或 CMD，然后运行：

```powershell
python --version
```

### 无法替换 CBZ

关闭 Calibre、Calibre-Web、漫画阅读器以及可能占用文件的窗口，再对副本重试。

### 删除子合集后 CBZ 无法打开

旧版删除工具曾对每个成员无条件启用 ZIP64。即使 CBZ 很小，成员也会被标记为需要 ZIP 4.5；Python 和部分解压工具仍能读取，但某些漫画阅读器可能拒绝打开。

修正版只在单个成员实际超过 ZIP32 限制时自动启用 ZIP64。遇到旧版生成的文件时，可在保留原文件的前提下重新打包；修复后应检查 CRC、图片页数、`ComicInfo.xml`、可逆清单以及普通成员的 ZIP 版本标记。

### GitHub Desktop 没有上传按钮

- `0 changed files`：没有新修改，不需要提交。
- `Commit to main`：先填写修改说明并提交。
- `Push origin`：本地有新提交，需要上传。
- `Fetch origin`：当前已同步，可检查远程更新。

## 10. 当前状态

`cbz-workflow` 当前状态为“测试中”。本地核心流程和真实小型 CBZ 副本已经通过测试；在完成超大文件、真实大合集和网络下载测试后，再考虑标记为“稳定”。
