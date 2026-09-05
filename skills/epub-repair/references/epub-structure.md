# EPUB 结构与修复边界

## 必需结构

- ZIP 根目录必须包含 `mimetype`，内容严格为 `application/epub+zip`；它应是第一个成员并使用 `ZIP_STORED`。
- `META-INF/container.xml` 指向一个或多个 OPF package document。
- OPF `manifest` 声明出版物资源，`spine` 通过 `idref` 指定默认阅读顺序。
- EPUB 3 通常用带 `properties="nav"` 的 XHTML 导航文档；EPUB 2 通常用 NCX。

## 可自动修复

- `mimetype` 缺失、位置错误、内容错误或被压缩：重建 ZIP 时写入正确的首个未压缩成员。
- `container.xml` 缺失或损坏，且压缩包内恰好只有一个 `.opf`：用该唯一 OPF 重建容器声明。
- 重新打包时保留其他成员、ZIP 注释及常用成员属性。

## 只报告、不自动猜测

- 存在多个 OPF 但容器声明缺失；
- manifest 指向的章节、图片、样式或字体不存在；
- spine 引用未知 ID，或阅读顺序需要语义判断；
- nav/NCX 缺失、目录标题错误或层级需要从正文推断；
- 重复路径、大小写冲突、路径穿越或加密内容；
- DRM、密码或供应商专有保护。

这些情况需要先列出准确文件和引用关系，再根据用户确认选择修复策略。

## 验证

修复后重新运行检查脚本。结构检查通过后，仍应在目标阅读器或 Calibre 中确认封面、目录跳转、章节顺序、图片、字体和特殊字符显示。
