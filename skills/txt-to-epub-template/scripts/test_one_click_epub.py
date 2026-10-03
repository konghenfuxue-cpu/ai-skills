import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from zipfile import ZipFile

from one_click_epub import infer_metadata, choose_output, prepare_text, inspect_epub, run, detect_number_gaps


class OneClickEpubTests(unittest.TestCase):
    def test_infer_metadata_from_chinese_filename(self):
        self.assertEqual(infer_metadata(Path("金色茉莉花 - 作者甲.txt")), ("金色茉莉花", "作者甲"))
        self.assertEqual(infer_metadata(Path("七等分的未来(李白不太白).txt")), ("七等分的未来", "李白不太白"))
        self.assertEqual(infer_metadata(Path("只有书名.txt")), ("只有书名", None))

    def test_choose_output_does_not_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="中文 空格 ") as temp:
            folder = Path(temp)
            first = choose_output(folder, "书名", "作者")
            first.write_bytes(b"old")
            second = choose_output(folder, "书名", "作者")
            self.assertNotEqual(first, second)
            self.assertEqual(first.read_bytes(), b"old")

    def test_prepare_text_only_removes_standalone_site_prompts(self):
        source = "第一章 开始\n『加入书签，方便阅读』\n他拿出书签。\n『点击章节报错』\n    &emsp;&emsp;正文。\n"
        prepared, counts = prepare_text(source)
        self.assertEqual(counts, {"加入书签，方便阅读": 1, "点击章节报错": 1})
        self.assertIn("他拿出书签。", prepared)
        self.assertIn("正文。", prepared)
        self.assertNotIn("&emsp;", prepared)

    def test_detect_number_gaps_with_combined_opening(self):
        text = "第一章到第三章 合章\n内容\n第四章 继续\n第六章 以后\n"
        self.assertEqual(detect_number_gaps(text), [5])

    def test_inspect_epub_rejects_broken_file(self):
        with tempfile.TemporaryDirectory(prefix="中文 空格 ") as temp:
            book = Path(temp) / "测试.epub"
            with ZipFile(book, "w") as archive:
                archive.writestr("mimetype", "application/epub+zip")
            result = inspect_epub(book)
            self.assertFalse(result["ok"])
            self.assertTrue(result["errors"])

    def test_end_to_end_with_chinese_and_space_path(self):
        candidates = (
            Path(__file__).with_name("txt_to_epub.py"),
            Path(__file__).resolve().parents[1] / "scripts" / "txt_to_epub.py",
        )
        builder = next((path for path in candidates if path.is_file()), None)
        if builder is None:
            self.skipTest("本机模板转换器不可用")
        with tempfile.TemporaryDirectory(prefix="中文 空格 ") as temp:
            folder = Path(temp)
            source = folder / "测试小说 - 作者甲.txt"
            source.write_text("第一章 开始\n『加入书签，方便阅读』\n正文第一段。\n第二章 继续\n正文第二段。\n", encoding="utf-8")
            args = Namespace(input=str(source), title=None, author=None, cover=None,
                             description="测试简介", output_dir=str(folder), builder=str(builder), no_gui=True)
            first, report, check = run(args)
            self.assertTrue(check["ok"], check["errors"])
            self.assertTrue(first.is_file())
            self.assertIn("网页提示清理：1 行", report.read_text(encoding="utf-8-sig"))
            with ZipFile(first) as book:
                text = book.read("OEBPS/Text/chapter-0001.xhtml").decode("utf-8")
                self.assertIn("正文第一段。", text)
                self.assertNotIn("加入书签", text)
            second, _, second_check = run(args)
            self.assertTrue(second_check["ok"])
            self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
