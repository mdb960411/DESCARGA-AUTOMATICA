import importlib.util
import unittest
from pathlib import Path

from app.config import Config
from app.utils import safe_filename, url_for_log


def load_filters():
    path = Path(__file__).parents[1] / "app" / "downloaders" / "filters.py"
    spec = importlib.util.spec_from_file_location("filters_standalone", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoreTests(unittest.TestCase):
    def test_graphic_extensions_are_enabled_by_default(self):
        expected = {".ai", ".ps", ".eps", ".indd", ".psd", ".tif"}
        self.assertTrue(expected.issubset(Config.allowed_extensions))

    def test_large_file_default_is_eight_gib(self):
        self.assertEqual(
            Config.max_file_size_bytes(),
            8192 * 1024 * 1024,
        )

    def test_email_asset_is_filtered_but_graphic_file_is_not(self):
        filters = load_filters()
        ignored, _ = filters.should_ignore_url(
            "https://www.sendgb.com/images/mail/border.png"
        )
        allowed, _ = filters.should_ignore_url(
            "https://files.example.com/trabajo.ai"
        )
        self.assertTrue(ignored)
        self.assertFalse(allowed)

    def test_url_token_is_not_logged(self):
        protected = url_for_log("https://sendgb.com/token-secreto?key=123")
        self.assertNotIn("token-secreto", protected)
        self.assertNotIn("key=123", protected)

    def test_graphic_filename_is_sanitized(self):
        self.assertEqual(safe_filename("arte:final.ai"), "arte_final.ai")


if __name__ == "__main__":
    unittest.main()
