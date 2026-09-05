---
name: calibre-workflow
description: 审计和安全整理本地 Calibre 书库，检查 metadata.db、格式文件、重复书籍候选和路径问题；当任务涉及 Calibre 书库检查、格式缺失、重复书整理或导入前诊断时使用。不用于绕过 DRM、直接修改 metadata.db 或推荐书籍。
---

# Calibre 书库工作流

处理具体书库前读取[书库审计与安全边界](references/library-audit.md)。

## 只读审计

使用 `scripts/audit_calibre_library.py` 扫描书库：

```powershell
python scripts/audit_calibre_library.py "D:\Calibre Library"
python scripts/audit_calibre_library.py "D:\Calibre Library" --report "D:\报告\calibre-audit.json"
```

脚本以 SQLite 只读模式打开 `metadata.db`，不会修改数据库、移动书籍、删除格式或调用 Calibre。

## 工作原则

1. 先确认 Calibre 已关闭或没有在写入书库；然后只读审计 `metadata.db`、书目、格式记录和对应文件。
2. 将标题相同或标题相似的项目标为“重复候选”，不自动合并、删除或覆盖。
3. 发现缺失格式文件、路径异常或数据库完整性问题时，先给出书籍 ID、标题、格式和预期路径；涉及修复、合并或删除时等待用户确认。
4. 修改书库优先通过 Calibre GUI、`calibredb` 或明确的备份/副本流程进行；绝不直接写 `metadata.db`。
5. 不移除或绕过 DRM；加密格式仅报告。
6. 处理完实际书库后，重新审计并由用户在 Calibre 中确认书目和格式可用。

## 完成标准

- 明确书库路径、数据库完整性、书籍数和格式数；
- 缺失文件与重复候选均能定位到具体书籍；
- 报告包含只读性质及待人工确认项；
- 未经确认不产生数据库或书籍文件修改。
