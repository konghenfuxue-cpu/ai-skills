import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from script_support import ROOT


class SkillSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pwsh = shutil.which("pwsh")
        if not cls.pwsh:
            raise RuntimeError("PowerShell 7 (pwsh) is required for the sync checker tests")
        cls.script = ROOT / "skills/skill-repository-manager/scripts/check-skill-repo.ps1"

    def write(self, root, relative, content="same"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def check(self, repo, installed, *options):
        result = subprocess.run([self.pwsh, "-NoProfile", "-File", str(self.script), "-Repository", str(repo), "-CodexSkills", str(installed), "-Json", "-FailOnDrift", *options], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertIn(result.returncode, (0, 1), result.stderr)
        self.assertTrue(result.stdout.lstrip().startswith("{"), result.stderr or result.stdout)
        return result.returncode, json.loads(result.stdout)

    def test_hash_drift_missing_extra_and_local_config_are_distinguished(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, installed = Path(directory) / "仓库", Path(directory) / "安装"
            source, copy = repo / "skills/example", installed / "example"
            for root in (source, copy):
                self.write(root, "SKILL.md")
                self.write(root, "scripts/tool.py")
                self.write(root, "references/local-settings.md", str(root))
            self.write(source, "missing.txt")
            self.write(copy, "scripts/tool.py", "changed")
            self.write(copy, "extra.txt")
            self.write(copy, "__pycache__/test.pyc")
            self.write(copy, ".venv/Lib/dependency.py")
            self.write(copy, "scripts/option.yml")
            self.write(installed / "independent", "SKILL.md")
            code, report = self.check(repo, installed)
            self.assertEqual(code, 1)
            skill = report["Skills"][0]
            self.assertFalse(skill["InSync"])
            self.assertEqual(skill["MissingFiles"], ["missing.txt"])
            self.assertEqual(skill["ChangedFiles"], ["scripts/tool.py"])
            self.assertEqual(skill["ExtraFiles"], ["extra.txt"])
            self.assertEqual(skill["LocalConfigDifferences"], ["references/local-settings.md"])
            self.assertEqual(report["UnmanagedSkills"], ["independent"])

    def test_only_local_config_difference_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, installed = Path(directory) / "repo", Path(directory) / "installed"
            for root in (repo / "skills/example", installed / "example"):
                self.write(root, "SKILL.md")
                self.write(root, "references/local-settings.md", str(root))
            code, report = self.check(repo, installed)
            self.assertEqual(code, 0)
            self.assertTrue(report["Skills"][0]["InSync"])

    def test_missing_installation_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, installed = Path(directory) / "repo", Path(directory) / "absent"
            self.write(repo / "skills/example", "SKILL.md")
            code, report = self.check(repo, installed)
            self.assertEqual(code, 1)
            self.assertFalse(report["Skills"][0]["Installed"])
            self.assertEqual(report["Skills"][0]["MissingFiles"], ["SKILL.md"])


if __name__ == "__main__":
    unittest.main()
