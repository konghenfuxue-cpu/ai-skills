from __future__ import annotations

import hashlib
import importlib.util
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(relative)
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class EpubRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.epub = load_script(
            "epub_repair_test",
            "skills/epub-repair/scripts/epub_check_repair.py",
        )

    def test_repairs_wrapper_to_new_file_without_changing_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.epub"
            output = root / "repaired.epub"
            opf = (
                b'<package xmlns="http://www.idpf.org/2007/opf">'
                b'<manifest><item id="chapter" href="chapter.xhtml" '
                b'media-type="application/xhtml+xml"/></manifest>'
                b'<spine><itemref idref="chapter"/></spine></package>'
            )
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("OEBPS/chapter.xhtml", b"<html/>")
                archive.writestr("OEBPS/content.opf", opf)
                archive.writestr("mimetype", self.epub.MIMETYPE_VALUE)
            original_hash = hashlib.sha256(source.read_bytes()).digest()

            before = self.epub.inspect_epub(source)
            self.assertIn("container_missing", {f.code for f in before["findings"]})
            after = self.epub.repair_epub(source, output, before)

            self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), original_hash)
            self.assertTrue(output.is_file())
            self.assertFalse(any(f.level == "ERROR" for f in after["findings"]))
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.infolist()[0].filename, "mimetype")
                self.assertEqual(archive.infolist()[0].compress_type, zipfile.ZIP_STORED)
                self.assertIn("OEBPS/content.opf", archive.read("META-INF/container.xml").decode())

    def test_ambiguous_opf_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "ambiguous.epub"
            output = root / "repaired.epub"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("a.opf", b"<package/>")
                archive.writestr("b.opf", b"<package/>")
            report = self.epub.inspect_epub(source)
            with self.assertRaises(ValueError):
                self.epub.repair_epub(source, output, report)
            self.assertFalse(output.exists())


class CalibreAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calibre = load_script(
            "calibre_audit_test",
            "skills/calibre-workflow/scripts/audit_calibre_library.py",
        )

    def test_audit_reports_missing_files_and_keeps_database_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Path(temporary)
            database = library / "metadata.db"
            with closing(sqlite3.connect(database)) as connection:
                with connection:
                    connection.executescript(
                        "CREATE TABLE books (id INTEGER, title TEXT, path TEXT);"
                        "CREATE TABLE data (book INTEGER, format TEXT, name TEXT);"
                        "INSERT INTO books VALUES (1, 'Example Book', 'Author/One');"
                        "INSERT INTO books VALUES (2, 'Example-Book', 'Author/Two');"
                        "INSERT INTO data VALUES (1, 'EPUB', 'Example');"
                        "INSERT INTO data VALUES (2, 'EPUB', 'Missing');"
                    )
            present = library / "Author" / "One" / "Example.epub"
            present.parent.mkdir(parents=True)
            present.write_bytes(b"sample")
            original_hash = hashlib.sha256(database.read_bytes()).digest()

            report = self.calibre.audit_library(library)

            self.assertTrue(report["read_only"])
            self.assertEqual(report["database_quick_check"], ["ok"])
            self.assertEqual(report["book_count"], 2)
            self.assertEqual(report["format_count"], 2)
            self.assertEqual(len(report["missing_format_files"]), 1)
            self.assertEqual(len(report["duplicate_title_candidates"]), 1)
            self.assertEqual(hashlib.sha256(database.read_bytes()).digest(), original_hash)
            self.assertFalse((library / "metadata.db-journal").exists())
            self.assertFalse((library / "metadata.db-wal").exists())


if __name__ == "__main__":
    unittest.main()
