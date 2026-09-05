from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块：{relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def member_digest(path: Path):
    with zipfile.ZipFile(path) as archive:
        return (
            archive.comment,
            {
                info.filename: hashlib.sha256(archive.read(info)).hexdigest()
                for info in archive.infolist()
                if not info.is_dir()
            },
        )


class SkillLayoutTests(unittest.TestCase):
    def test_every_skill_has_valid_entry(self):
        for skill_dir in (ROOT / "skills").iterdir():
            if not skill_dir.is_dir():
                continue
            entry = skill_dir / "SKILL.md"
            self.assertTrue(entry.is_file(), skill_dir.name)
            text = entry.read_text(encoding="utf-8-sig")
            self.assertTrue(text.startswith("---\n"), skill_dir.name)
            self.assertIn(f"name: {skill_dir.name}\n", text, skill_dir.name)


class CbzWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.merge = load_module(
            "merge_smoke",
            "skills/cbz-workflow/scripts/reversible-merge-split/merge_cbz.py",
        )
        cls.split = load_module(
            "split_smoke",
            "skills/cbz-workflow/scripts/reversible-merge-split/split_cbz_collection.py",
        )
        cls.remove = load_module(
            "remove_smoke",
            "skills/cbz-workflow/scripts/remove-subcollection/remove_cbz_subcollection.py",
        )

    @staticmethod
    def make_source(path: Path, title: str, marker: bytes):
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>'
            f"<ComicInfo><Title>{title}</Title><PageCount>2</PageCount></ComicInfo>"
        ).encode()
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.comment = b"comment-" + marker
            archive.writestr("001.jpg", marker + b"-1")
            archive.writestr("002.jpg", marker + b"-2")
            archive.writestr("ComicInfo.xml", xml)

    def test_reversible_merge_split_and_remove(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            first = work / "第1话.cbz"
            second = work / "第2话.cbz"
            self.make_source(first, "第一话", b"one")
            self.make_source(second, "第二话", b"two")
            originals = {path.name: member_digest(path) for path in (first, second)}

            merged = work / "合集.cbz"
            log = self.merge.ProgressLog(work / "merge.log")
            try:
                ordered, pages = self.merge.merge_cbz(
                    [second, first], merged, "测试合集", log
                )
            finally:
                log.close()
            self.assertEqual([path.name for path in ordered], [first.name, second.name])
            self.assertEqual(pages, 4)

            with zipfile.ZipFile(merged) as archive:
                self.assertIsNone(archive.testzip())
                manifest = json.loads(
                    archive.read(self.merge.MANIFEST_PATH).decode("utf-8")
                )

            restored_dir = work / "restored"
            restored_dir.mkdir()
            restored = self.split.restore_reversible(
                merged, restored_dir, manifest
            )
            for path in restored:
                self.assertEqual(member_digest(path), originals[path.name])

            analysis = self.remove.analyze(merged, 1)
            removed = work / "删除第一项.cbz"
            result = self.remove.rewrite_cbz(merged, removed, 1, analysis)
            self.assertTrue(result["manifest_updated"])
            with zipfile.ZipFile(removed) as archive:
                updated = json.loads(
                    archive.read(self.merge.MANIFEST_PATH).decode("utf-8")
                )
                self.assertEqual(len(updated["sources"]), 1)
                self.assertEqual(updated["sources"][0]["original_name"], second.name)


if __name__ == "__main__":
    unittest.main()
