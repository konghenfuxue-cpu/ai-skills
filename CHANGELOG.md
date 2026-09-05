# 变更日志

本项目采用语义化版本号：修复为 PATCH，新兼容功能为 MINOR，不兼容变化为 MAJOR。

## Unreleased

### Added

- 公开版安装与使用教程。
- 贡献指南、安全策略、行为准则、Issue/PR 模板和自动回归测试。

### Changed

- 项目展示名称更新为“数字书库与漫画 Agent Skills”。
- 公开文档和 Skill 配置改用通用路径。
- JMComic 工具支持 `JMCOMIC_DOWNLOAD_ROOT` 或运行时输入下载根目录。

## 1.0.0 - 2026-09-05

### Added

- `cbz-workflow`：页数与元数据、可逆合并/拆分、删除子合集、报告检查和本地打包。
- `epub-repair`：EPUB 结构检查和安全包装修复。
- `calibre-workflow`：Calibre 书库只读审计。
- `skill-repository-manager`：Skill 创建、验证、提交、安装和同步流程。

### Verified

- 300 页 CBZ 合集与超过 2 GiB ZIP64 成员的流式处理。
- 删除可逆合集来源后同步更新合并清单并保留剩余拆分能力。
- 真实 EPUB 的只读检查和临时损坏副本修复。
- 真实 Calibre 书库的只读审计。
