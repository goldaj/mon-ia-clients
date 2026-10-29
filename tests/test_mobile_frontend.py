"""Check PWA markup contract without importing FastAPI or touching a server."""
import ast
import re
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "mobile" / "app.py"


class MobileMarkupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        cls.constants = {
            target.id: value
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
            if isinstance(value := node.value, ast.Constant) and isinstance(value.value, str)
        }
        cls.page = cls.constants["INDEX"].value

    def test_buttons_file_picker_and_library_script(self):
        for marker in ('id="exportBtn"', 'id="importBtn"', 'id="backupFile"',
                       'src="/conversation_backup.js"', 'backupInput.onchange=importHistory'):
            self.assertIn(marker, self.page)

    def test_no_upload_endpoint_added_to_backup(self):
        self.assertNotIn('fetch("/api/backup"', self.page)
        self.assertNotIn('FormData(', self.page)
        self.assertIn('new Blob(', self.page)
        self.assertIn('URL.createObjectURL(blob)', self.page)

    def test_service_worker_updates_cache(self):
        worker = self.constants["SERVICE_WORKER"].value
        self.assertIn('/conversation_backup.js', worker)
        self.assertIn('mon-ia-v2-history-backup', worker)
        self.assertIn('e.request.method!=="GET"', worker)

    def test_one_inline_script_for_optional_node_syntax_check(self):
        matches = re.findall(r"<script>(.*?)</script>", self.page, flags=re.S)
        self.assertEqual(len(matches), 1)
        self.assertIn('function importHistory()', matches[0])


if __name__ == "__main__":
    unittest.main()
