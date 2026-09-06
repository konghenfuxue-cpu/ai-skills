# 变更日志

本项目采用语义化版本号：修复为 PATCH，新兼容功能为 MINOR，不兼容变化为 MAJOR。

## Unreleased

### Changed

- README 当前稳定版更新为 `v1.0.1`，并增加测试、最新版本和 MIT 许可证徽章。
- 根据 GPT-6 Astra 的提示设计建议精简四个个人 Skill：缩短触发描述，改为按需读取与按影响验证，并让任务内已有授权持续有效。
- Skill 仓库管理流程改为先同步私有 `backup`，审查相对公开仓库新增的完整历史后再同步 `origin`。

## 1.0.1 - 2026-09-06

### Added

- 公开版安装与使用教程。
- 贡献指南、安全策略、行为准则、Issue/PR 模板和自动回归测试。

### Changed

- 项目展示名称更新为“数字书库与漫画 Agent Skills”。
- 公开文档和 Skill 配置改用通用路径。
- JMComic 工具支持 `JMCOMIC_DOWNLOAD_ROOT` 或运行时输入下载根目录。
- GitHub Actions 在 Windows Runner 中固定使用 UTF-8，并升级到 Node.js 24 运行环境。

### Verified

- Python 3.11 和 3.12 的编译检查与 CBZ 可逆合并、拆分、删除自动测试通过。

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
