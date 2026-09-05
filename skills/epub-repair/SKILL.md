---
name: epub-repair
description: 检查和安全修复本地 EPUB 的 ZIP 包装、mimetype、container.xml、OPF manifest/spine 与目录引用；当任务涉及 EPUB 无法打开、目录失效、结构损坏或 Calibre 导入失败时使用。不用于电子书推荐、内容改写或 DRM 移除。
---

# EPUB 检查与修复

先识别故障层级，再决定是否修改。处理具体文件前读取[EPUB 结构与修复边界](references/epub-structure.md)。

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

- 输出文件存在且非空；
- ZIP 可完整读取；
- `mimetype` 为首个未压缩成员且内容准确；
- `container.xml` 可定位并解析 OPF；
- manifest 和 spine 引用均有明确检查结果；
- 报告仍未解决的问题，不能把部分修复称为完全成功。
