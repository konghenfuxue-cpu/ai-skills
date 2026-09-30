import io
import posixpath
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

from script_support import load_script


class TxtEpubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = load_script("txt_epub_safety", "skills/txt-to-epub-template/scripts/txt_to_epub.py")

    def args(self, source, output, *extra):
        with patch.object(sys, "argv", ["txt_to_epub.py", str(source), "--title", "测试 & 书名", "--author", "测试作者", "--output", str(output), *extra]):
            return self.tool.parse_args()

    def test_generated_epub_links_spine_and_trailing_extra_group(self):
        for afterword_last in (False, True):
            with self.subTest(afterword_last=afterword_last), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "中文 原稿.txt"
                output = Path(directory) / "新书.epub"
                extras = "番外一 晨光\n番外内容一\n番外二 暮色\n番外内容二\n"
                afterword = "完本感言\n作者自己的感言。\n"
                source.write_text("本文件来自测试书院\n简介保留。\n第一卷 起程\n第一章 出发\n角色提到了书友群，但这是正文。\n番外 途中\n中途番外内容\n第二章 继续\n正文继续。\n" + (extras + afterword if afterword_last else afterword + extras), encoding="gb18030")
                original = source.read_bytes()
                with redirect_stdout(io.StringIO()):
                    self.tool.build(self.args(source, output))
                self.assertEqual(source.read_bytes(), original)
                with zipfile.ZipFile(output) as archive:
                    self.assertIsNone(archive.testzip())
                    first = archive.infolist()[0]
                    self.assertEqual((first.filename, first.compress_type), ("mimetype", zipfile.ZIP_STORED))
                    self.assertEqual(archive.read("mimetype"), b"application/epub+zip")
                    container = ET.fromstring(archive.read("META-INF/container.xml"))
                    opf_path = container.find(".//{*}rootfile").get("full-path")
                    opf = ET.fromstring(archive.read(opf_path))
                    manifest = {item.get("id"): posixpath.normpath(posixpath.join(posixpath.dirname(opf_path), item.get("href"))) for item in opf.findall("{*}manifest/{*}item")}
                    for path in manifest.values():
                        self.assertIn(path, archive.namelist())
                    spine = [manifest[item.get("idref")] for item in opf.findall("{*}spine/{*}itemref")]
                    all_text = ""
                    for path in archive.namelist():
                        if not path.endswith(".xhtml"):
                            continue
                        text = archive.read(path).decode("utf-8")
                        all_text += text
                        document = ET.fromstring(text)
                        for node in document.iter():
                            for attribute in ("href", "src"):
                                link = node.get(attribute)
                                if not link:
                                    continue
                                url = urlsplit(link)
                                if url.scheme or url.netloc:
                                    continue
                                target = posixpath.normpath(posixpath.join(posixpath.dirname(path), unquote(url.path))) if url.path else path
                                self.assertIn(target, archive.namelist(), (path, link))
                    self.assertNotIn("本文件来自测试书院", all_text)
                    self.assertIn("角色提到了书友群，但这是正文。", all_text)
                    nav = ET.fromstring(archive.read("OEBPS/Text/nav.xhtml"))
                    top_items = nav.findall(".//{*}nav/{*}ol/{*}li")
                    top_links = {item.find("{*}a").text: item for item in top_items}
                    self.assertIn("完本感言", top_links)
                    group = top_links["番外"]
                    children = group.findall("{*}ol/{*}li/{*}a")
                    self.assertEqual([child.text for child in children], ["番外一 晨光", "番外二 暮色"])
                    group_path = "OEBPS/Text/" + group.find("{*}a").get("href")
                    first_extra = "OEBPS/Text/" + children[0].get("href")
                    self.assertEqual(spine.index(group_path) + 1, spine.index(first_extra))

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "原稿.txt", Path(directory) / "已有.epub"
            source.write_text("第一章 开始\n正文", encoding="utf-8")
            output.write_bytes(b"existing book")
            with self.assertRaises(SystemExit):
                self.tool.build(self.args(source, output))
            self.assertEqual(output.read_bytes(), b"existing book")

    def test_late_output_creation_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "原稿.txt", Path(directory) / "并发.epub"
            source.write_text("第一章 开始\n正文", encoding="utf-8")
            read_text = self.tool.read_text

            def concurrent_creation(path):
                output.write_bytes(b"another process")
                return read_text(path)

            with patch.object(self.tool, "read_text", side_effect=concurrent_creation):
                with self.assertRaises(FileExistsError):
                    self.tool.build(self.args(source, output))
            self.assertEqual(output.read_bytes(), b"another process")

    def test_write_failure_removes_partial_output_and_keeps_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "原稿.txt", Path(directory) / "失败.epub"
            source.write_text("第一章 开始\n正文", encoding="utf-8")
            original = source.read_bytes()
            with patch.object(self.tool, "ASSETS", Path(directory) / "missing-assets"):
                with self.assertRaises(FileNotFoundError):
                    self.tool.build(self.args(source, output))
            self.assertFalse(output.exists())
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(list(Path(directory).iterdir()), [source])


if __name__ == "__main__":
    unittest.main()
