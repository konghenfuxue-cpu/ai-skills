import os
import shutil
import subprocess
import tempfile
import unittest
import venv
from pathlib import Path

from script_support import ROOT


@unittest.skipUnless(os.name == "nt", "Windows CMD launcher")
class DownloadLauncherTests(unittest.TestCase):
    def test_exit_menu_uses_pinned_environment_with_unicode_and_spaces(self):
        tool = ROOT / "skills/cbz-workflow/scripts/jmcomic-download-pack"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "中文 工具"
            target.mkdir()
            for name in ("一键下载并转CBZ.cmd", "requirements.txt", "check_dependencies.py"):
                shutil.copy2(tool / name, target / name)
            (target / "option.yml").write_text("{}", encoding="utf-8")
            # Reuse already-installed test dependencies, so the fixture needs no download.
            venv.EnvBuilder(system_site_packages=True, with_pip=False).create(target / ".venv")
            environment = os.environ.copy()
            environment.update(PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
            menu = Path(directory) / "menu.txt"
            menu.write_bytes(b"\r\n4\r\n\r\n")
            with menu.open("rb") as stdin:
                result = subprocess.run(
                    [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", str(target / "一键下载并转CBZ.cmd")],
                    stdin=stdin, capture_output=True, text=True, errors="replace",
                    env=environment, timeout=15,
                )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Pinned dependency versions and imports OK.", result.stdout)
            self.assertIn("4. Exit", result.stdout)
            self.assertNotIn("[ERROR]", result.stdout)
            self.assertNotIn("Installing pinned", result.stdout)


if __name__ == "__main__":
    unittest.main()
