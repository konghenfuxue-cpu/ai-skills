# 本地环境配置模板

公开仓库只提供通用默认值。维护者或使用者应把自己的绝对路径记录在仓库根目录中被 Git 忽略的 `LOCAL.md`，不要提交个人目录、Cookie、Token 或账号配置。

## 路径约定

- JMComic 下载根目录：环境变量 `JMCOMIC_DOWNLOAD_ROOT`；未设置时由工具询问或使用 `%USERPROFILE%\Downloads\JMComic`。
- CBZ 输出目录：`<JMComic 下载根目录>\CBZ`。
- 其他漫画或电子书目录：由用户在每次任务中明确提供。

## 软件

- Windows 11
- PowerShell 7
- Python 3.11 或更高版本
- Calibre（可选）
- Calibre-Web
- OpenComic

## 用户偏好

- 批量元数据处理默认先使用副本；是否原地更新由使用者明确确认；
- 第一次运行新脚本时使用测试副本；
- 保留原简介和原元数据，新内容换行追加；
- 处理结束后显示成功、失败和跳过数量；
- 支持 2 GB 以上的 CBZ；
- CMD 文件需要兼容中文路径和 UTF-8 编码。
