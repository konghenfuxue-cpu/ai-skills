---
name: epub-repair
description: 检查并安全修复本地 EPUB 的 ZIP 包装、container.xml、OPF、spine 和目录引用；用于 EPUB 结构损坏或导入失败。
---

# EPUB 检查与修复

先识别故障层级。普通结构检查可直接使用脚本；需要修复或解释不确定问题时，读取[EPUB 结构与修复边界](references/epub-structure.md)。

## 工具

使用 `scripts/epub_check_repair.py` 执行可重复的结构检查和安全修复：

```powershell
python scripts/epub_check_repair.py "书名.epub"
python scripts/epub_check_repair.py "书名.epub" --repair
```

默认只检查。`--repair` 生成新的“原名_已修复.epub”，不覆盖原文件。

## 工作原则

1. 先检查 ZIP、`mimetype`、`META-INF/container.xml`、OPF、manifest、spine 和导航文档。
2. 自动修复只处理可确定恢复的问题：重建标准 EPUB ZIP 包装；当压缩包中仅有一个 OPF 时，可重建缺失或损坏的 `container.xml`。
3. 缺失章节、错误阅读顺序或目录文字需要结合内容判断时，只报告证据，不猜测生成正文或目录。
4. 保留原 EPUB、未知文件、ZIP 注释和成员属性；大文件采用流式复制。
5. 不移除或绕过 DRM。发现加密声明时报告并停止内容级修改。
6. 第一次处理真实书籍时使用副本；修复后重新检查，并建议用 Calibre 或阅读器人工打开确认。

## 完成标准

- 只检查：报告 ZIP、`mimetype`、container、OPF、manifest、spine 和导航引用的检查结果，并定位发现的问题。
- 执行修复：输出文件存在且非空，ZIP 可完整读取，修复目标已重新检查，同时报告仍未解决的问题。
- 只有全部相关检查通过时才报告完全成功。
