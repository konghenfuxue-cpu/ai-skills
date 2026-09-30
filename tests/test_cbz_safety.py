import io
import json
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from xml.etree import ElementTree as ET

from PIL import Image

from script_support import load_script


class PagecountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = load_script("pagecount_safety", "skills/cbz-workflow/scripts/pagecount-metadata/cbz_pagecount_metadata.py")

    def make_cbz(self, path):
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("001.jpg", b"a" * (2 * 1024 * 1024))
            archive.writestr("第二页.AVIF", b"b")
            archive.writestr(".hidden.jpg", b"hidden")
            archive.writestr("__MACOSX/003.jpg", b"hidden")
            archive.writestr("ComicInfo.xml", "<ComicInfo><Title>测试标题</Title><Writer>原作者</Writer><Summary>原简介\n页数：99 页</Summary><Custom keep='yes'>保留</Custom></ComicInfo>".encode())
            archive.comment = json.dumps({"custom": "keep", "ComicBookInfo/1.0": {"tags": ["保留标签"]}}, ensure_ascii=False).encode()

    def test_streams_pages_preserves_metadata_and_does_not_duplicate_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "中文 空格.cbz"
            self.make_cbz(path)
            original_read = zipfile.ZipFile.read

            def metadata_only(archive, name, *args, **kwargs):
                filename = name.filename if isinstance(name, zipfile.ZipInfo) else name
                if self.tool.is_page_image(filename):
                    raise AssertionError("Image entries must be copied as streams")
                return original_read(archive, name, *args, **kwargs)

            with patch.object(zipfile.ZipFile, "read", metadata_only):
                for _ in range(2):
                    pages, _ = self.tool.update_cbz(path, make_backup=False)
                    self.assertEqual(pages, 2)
            with zipfile.ZipFile(path) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(archive.read("001.jpg"), b"a" * (2 * 1024 * 1024))
                xml = ET.fromstring(archive.read("ComicInfo.xml"))
                self.assertEqual(xml.findtext("Title"), "测试标题")
                self.assertEqual(xml.findtext("Writer"), "原作者")
                self.assertEqual(xml.find("Custom").attrib, {"keep": "yes"})
                self.assertEqual(xml.findtext("Custom"), "保留")
                self.assertEqual(xml.findtext("Summary"), "原简介\n\n页数：2 页")
                comment = json.loads(archive.comment)
                self.assertEqual(comment["custom"], "keep")
                self.assertEqual(comment["ComicBookInfo/1.0"]["tags"], ["保留标签"])
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_replace_failure_keeps_original_and_removes_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "原文件.cbz"
            self.make_cbz(path)
            original = path.read_bytes()
            with patch.object(self.tool.os, "replace", side_effect=PermissionError("busy")):
                with self.assertRaises(PermissionError):
                    self.tool.update_cbz(path, make_backup=False)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_duplicate_member_names_keep_their_own_bytes(self):
        with tempfile.TemporaryDirectory() as directory, warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Duplicate name:")
            path = Path(directory) / "重复名称.cbz"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("001.jpg", b"first")
                archive.writestr("001.jpg", b"second")
            self.tool.update_cbz(path, make_backup=False)
            with zipfile.ZipFile(path) as archive:
                self.assertEqual([archive.read(info) for info in archive.infolist() if info.filename == "001.jpg"], [b"first", b"second"])


class PackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = load_script("pack_safety", "skills/cbz-workflow/scripts/jmcomic-download-pack/pack_cbz.py")

    def chapter(self, directory):
        images = []
        for number in (1, 2):
            path = directory / f"{number:03d}.jpg"
            Image.new("RGB", (80, 120), (20, 40, 60)).save(path)
            images.append(path)
        return self.tool.Chapter(directory, images, 1, "第1话", actual_no=1)

    def test_pack_creates_readable_images_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            chapter = self.chapter(root)
            output = root / "正常 分卷.cbz"
            self.tool.make_cbz(output, [chapter], None, 40, 85)
            self.assertEqual(self.tool.write_pagecount_in_place(output, "测试作者"), 2)
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(ET.fromstring(archive.read("ComicInfo.xml")).findtext("Writer"), "测试作者")
                with Image.open(io.BytesIO(archive.read("001/0001.jpg"))) as image:
                    self.assertEqual(image.size, (40, 60))

    def test_pack_failures_keep_previous_output_and_clean_temps(self):
        for notice in (False, True):
            for failure in (OSError("write interrupted"), KeyboardInterrupt()):
                with self.subTest(notice=notice, failure=type(failure).__name__), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    chapter = self.chapter(root)
                    output = root / "已有.cbz"
                    output.write_bytes(b"previous output")
                    before = set(root.iterdir())
                    with patch.object(self.tool, "processed_image_bytes", side_effect=[b"first page", failure]):
                        with self.assertRaises(type(failure)):
                            if notice:
                                self.tool.make_notice_cbz(output, [chapter], 40, 85)
                            else:
                                self.tool.make_cbz(output, [chapter], None, 40, 85)
                    self.assertEqual(output.read_bytes(), b"previous output")
                    self.assertEqual(set(root.iterdir()), before)

    def test_failed_crc_validation_does_not_replace_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            chapter = self.chapter(root)
            output = root / "已有.cbz"
            output.write_bytes(b"previous output")
            before = set(root.iterdir())
            with patch.object(zipfile.ZipFile, "testzip", return_value="001/0001.jpg"):
                with self.assertRaises(zipfile.BadZipFile):
                    self.tool.make_cbz(output, [chapter], None, 40, 85)
            self.assertEqual(output.read_bytes(), b"previous output")
            self.assertEqual(set(root.iterdir()), before)

    def test_integrity_reports_missing_corrupt_and_unavailable_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            chapter = self.chapter(Path(directory))
            chapter.images[1].write_bytes(b"corrupt image")
            metadata = {1: {"photo_id": "1", "title": "第一话"}, 2: {"photo_id": "2", "title": "第二话"}}

            def get_photo(photo_id, fetch_album):
                if photo_id == "2":
                    raise OSError("offline")
                return SimpleNamespace(page_arr=["1.webp", "2.webp", "3.webp"])

            rows, errors = self.tool.verify_download(metadata, [chapter], SimpleNamespace(get_photo_detail=get_photo))
            self.assertEqual(rows[0].missing, ["3.webp"])
            self.assertEqual(rows[0].corrupt, ["002.jpg"])
            self.assertEqual((rows[0].expected, rows[0].downloaded), (3, 2))
            self.assertEqual(rows[1].downloaded, 0)
            self.assertEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
