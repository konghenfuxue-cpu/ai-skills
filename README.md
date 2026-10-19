<h1 align="center">数字书库与漫画 Agent Skills</h1>

<p align="center">检查 EPUB、整理 CBZ、制作 EPUB，让重复的文件处理有一套可复用流程。</p>

<p align="center">
  <a href="https://github.com/konghenfuxue-cpu/ai-skills/archive/refs/heads/main.zip"><img src="https://img.shields.io/badge/Download-Source_ZIP-2563eb?style=for-the-badge&logo=github&logoColor=white" alt="下载当前工具集源码 ZIP"></a>
  <a href="新手入门.md"><img src="https://img.shields.io/badge/Read-Getting_Started-334155?style=for-the-badge" alt="阅读新手安装与使用教程"></a>
</p>

[![Tests](https://github.com/konghenfuxue-cpu/ai-skills/actions/workflows/tests.yml/badge.svg)](https://github.com/konghenfuxue-cpu/ai-skills/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-5c8b84)](LICENSE)

**[下载工具集](https://github.com/konghenfuxue-cpu/ai-skills/archive/refs/heads/main.zip) · [从零开始](新手入门.md) · [按任务选工具](#先选你要完成的任务)**

这里有可直接运行的 Python 脚本，也有供 Codex 读取的 Skill。第一次只检查一个 EPUB 副本，不必安装全部 Skill。项目不附书籍、漫画或独立图形界面。

本页与新手教程对应 `main`；[最新正式标签 v1.1.0](https://github.com/konghenfuxue-cpu/ai-skills/releases/tag/v1.1.0) 是较早的源码快照，没有 EXE，缺少后续部分内容。

## 实际效果

下面是原创两章 TXT 的实跑结果，文件路径已简化。转换与检查均退出 0：

```text
输入：练习.txt → 输出：我的练习.epub
识别：0 卷，2 个正文段落
目录：两章均有可解析的跳转目标
ZIP 成员：17
[通过] 未发现结构问题。
```

生成了新 EPUB，原 TXT 的 SHA-256 未变。这里展示的是脚本结果；阅读器视觉与 Codex 自动发现不在这项结果内。[查看验证范围](docs/beginner-verification.md)

## 三步开始

| 步骤 | 操作 | 结果 |
| --- | --- | --- |
| 1 · 下载 | 下载上方 ZIP，全部解压，进入直接含 `README.md` 和 `skills` 的那层 | 本地有完整脚本和资源，无需 Git |
| 2 · 准备 Python | 按[新手教程](新手入门.md#2-安装-python并确认能调用)安装或确认 Python 3.11，再创建 `.venv` | 使用项目独立环境；基础 EPUB 检查不需第三方包 |
| 3 · 检查副本 | 把一个合法 EPUB 副本放进 `练习文件`，命名为 `示例.epub`，运行下方命令 | 终端显示基础检查结果，不改书籍 |

在解压后的仓库根目录打开 PowerShell：

```powershell
.\.venv\Scripts\python.exe -X utf8 .\skills\epub-repair\scripts\epub_check_repair.py '.\练习文件\示例.epub'
```

需要 Codex 协助时，再按[教程的可选安装步骤](新手入门.md#5-可选让-codex-使用一个-skill)安装一个完整 Skill。当前官方目录与既有旧目录可能不同，先确认当前客户端使用的位置，不要直接覆盖已有安装。

## 先选你要完成的任务

| 任务 | 工具 | 入口 |
| --- | --- | --- |
| 检查、合并、拆分 CBZ，维护可逆合集 | `cbz-workflow` | [CBZ 使用说明](CBZ-Workflow使用说明.md) |
| 检查 EPUB 包装与基础结构 | `epub-repair` | [检查与修复边界](skills/epub-repair/SKILL.md) |
| 把中文 TXT 制作为带目录的 EPUB | `txt-to-epub-template` | [制作说明](skills/txt-to-epub-template/SKILL.md) |
| 查 Calibre 缺失文件与重复候选 | `calibre-workflow` | [只读审计](skills/calibre-workflow/SKILL.md) |
| 润色中文并保留原意与确定程度 | `humanizer-zh` | [使用与示例](skills/humanizer-zh/README.md) |

另有 Skill 仓库管理和私人纠错记忆工具，属于维护辅助功能；处理一本书不必全装。主要验证环境是 Windows 11、Python 3.11，维护流程另使用 PowerShell 7。

## 常见问题

**可以不装 Codex 吗？** 可以。文件检查、转换等核心脚本可用 Python 直接运行；让 AI 按 Skill 工作流执行才需要相应客户端。

**为什么没有窗口？** 命令行结果显示在终端。请在 PowerShell 运行，不要根据双击 `.py` 后窗口一闪而过判断成功。

**检查通过等于书籍完全没问题吗？** 不等于。基础结构检查不能代替正文核对、目标阅读器和完整 EPUBCheck 验收。

**修复会覆盖已有文件吗？** 首次只检查。修复或转换请用副本和全新输出名；当前 EPUB 修复入口对已有输出的保护有限，不能据“生成新文件”的说明放心复用旧输出路径。

**要装 JMComic 依赖吗？** 基础 EPUB/Calibre 检查不需要。只有下载及图片处理路线才按[教程](新手入门.md#6-其他任务需要什么)在同一虚拟环境安装固定依赖；依赖加载通过不代表网络站点可用。

**数据在哪里？** 原稿保留在你选的位置，输出与报告由命令参数或对应入口决定，不会自动上传或跨设备同步。不要将真实书籍、Cookie 或凭据提交 GitHub。

<details>
<summary>更多调用示例、安装边界与维护说明</summary>

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

</details>

## 来源与致谢

本仓库采用 [MIT 许可](LICENSE)。中文润色工具的上游来源与许可单独列在 [humanizer-zh 说明](skills/humanizer-zh/README.md#来源与许可)。参与维护前请阅读 [贡献说明](CONTRIBUTING.md) 与 [安全说明](SECURITY.md)。
