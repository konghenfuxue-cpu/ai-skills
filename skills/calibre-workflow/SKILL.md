---
name: calibre-workflow
description: 只读审计本地 Calibre 书库的 metadata.db、格式文件、异常路径和重复候选；用于书库检查、导入前诊断或整理前评估。
---

# Calibre 书库工作流

普通只读审计可直接使用脚本；需要解释修复边界或规划整理操作时，读取[书库审计与安全边界](references/library-audit.md)。

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
6. 实际修改书库后重新审计，并在 Calibre 中确认书目和格式可用；只读审计完成报告即可结束。

## 完成标准

- 只读审计：明确书库路径、数据库完整性、书籍数和格式数，并把缺失文件与重复候选定位到具体书籍。
- 整理任务：完成已授权的操作后重新审计，报告结果与仍需人工判断的项目。
