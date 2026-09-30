# 贡献指南

感谢你愿意改进“数字书库与漫画 Agent Skills”。本项目欢迎错误修复、兼容性改进、文档完善和新的隔离测试。

## 开始之前

1. 先搜索现有 Issue，确认问题尚未被报告。
2. 涉及行为变化时，建议先创建 Issue 说明使用场景和预期结果。
3. 不要上传真实漫画、电子书、Calibre 书库、下载日志、Cookie、Token 或账号凭据。
4. 不接受 DRM 绕过、未授权内容获取或隐藏网络行为。

## 本地开发

```powershell
git clone https://github.com/konghenfuxue-cpu/ai-skills.git
Set-Location '.\ai-skills'
python -m venv .venv
& '.\.venv\Scripts\Activate.ps1'
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
python -m pip install -r skills/cbz-workflow/scripts/jmcomic-download-pack/requirements.txt
python -m pip check
python skills/cbz-workflow/scripts/jmcomic-download-pack/check_dependencies.py
python -m compileall -q skills tests
python -m unittest discover -s tests -v
```

完整测试需要 Python 3.11 或更高版本、PowerShell 7 (`pwsh`) 和上述依赖。打包、图片处理、缺页报告通过生成的小样本及模拟站点响应验证；测试不连接 JMComic 网站，也不需要 option.yml。安装依赖需要联网。CI 在 Windows 的 Python 3.11 和 3.12 环境安装固定依赖并运行同一套测试；真实下载仍需单独验证。

## 修改要求

- 每个 Skill 的入口必须命名为 `SKILL.md`，YAML `name` 与目录名一致。
- 保留已有元数据和不冲突的旧功能。
- 文件操作默认使用副本或新输出；覆盖、删除和网络请求必须清楚提示。
- 大文件采用流式处理，不把整个压缩包成员一次读入内存。
- 新增脚本应支持中文、日文、空格和特殊字符路径。
- 重要行为变化应更新 `evals/`、使用说明和 `CHANGELOG.md`。

## Pull Request

1. 从最新 `main` 创建分支。
2. 只提交与本次改动相关的文件。
3. 运行语法检查和自动测试。
4. 在 PR 中说明修改原因、测试方法、结果和仍未覆盖的场景。
5. 涉及文件删除、覆盖、网络访问或数据库操作时，明确说明安全边界。

提交贡献即表示你同意该贡献按仓库的 [MIT License](LICENSE) 发布。
