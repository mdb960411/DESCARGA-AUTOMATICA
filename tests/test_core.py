import importlib.util
import unittest
from pathlib import Path

from app.browser_profile import (
    USER_AGENT,
    browser_context_options,
    browser_launch_arguments,
)
from app.config import Config
from app.download_result import DownloadResult
from app.link_utils import canonical_link_key
from app.status import execution_status, manual_action_for_reason
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

    def test_download_result_supports_multiple_files(self):
        result = DownloadResult.from_value(
            [Path("LINK 4.zip"), Path("LINK 2.zip")],
            default_error="error",
        )
        self.assertEqual(
            [path.name for path in result.paths],
            ["LINK 4.zip", "LINK 2.zip"],
        )
        self.assertEqual(result.errors, [])

    def test_empty_download_result_has_an_error(self):
        result = DownloadResult.from_value(
            None,
            default_error="La descarga no se completó",
        )
        self.assertEqual(result.paths, [])
        self.assertEqual(
            result.errors,
            ["La descarga no se completó"],
        )

    def test_manual_download_result_is_not_converted_to_error(self):
        result = DownloadResult.from_value(
            DownloadResult(
                manual_actions=["Requiere intervención manual"],
            ),
            default_error="error",
        )
        self.assertEqual(result.errors, [])
        self.assertEqual(
            result.manual_actions,
            ["Requiere intervención manual"],
        )

    def test_wetransfer_variants_share_a_canonical_key(self):
        first = canonical_link_key(
            "https://wetransfer.com/downloads/transfer123/secret456/file-a"
        )
        second = canonical_link_key(
            "https://wetransfer.com/downloads/transfer123/secret456/file-b?utm=1"
        )
        self.assertEqual(first, second)

    def test_ignored_email_label_is_configured(self):
        self.assertEqual(
            Config.ignored_label,
            "Descarga-Automatica-Ignorado",
        )

    def test_manual_email_label_is_configured(self):
        self.assertEqual(
            Config.manual_label,
            "Descarga-Automatica-Manual",
        )

    def test_compatibility_profile_uses_native_browser_features(self):
        options = browser_context_options(compatibility_mode=True)
        arguments = browser_launch_arguments(compatibility_mode=True)

        self.assertEqual(options["service_workers"], "allow")
        self.assertNotIn("user_agent", options)
        self.assertNotIn("--disable-background-networking", arguments)

    def test_optimized_profile_keeps_existing_oom_guards(self):
        options = browser_context_options(compatibility_mode=False)
        arguments = browser_launch_arguments(compatibility_mode=False)

        self.assertEqual(options["service_workers"], "block")
        self.assertEqual(options["user_agent"], USER_AGENT)
        self.assertIn("--renderer-process-limit=2", arguments)

    def test_modern_profile_uses_native_user_agent_with_oom_guards(self):
        options = browser_context_options(
            compatibility_mode=False,
            native_user_agent=True,
        )
        arguments = browser_launch_arguments(
            compatibility_mode=False,
        )

        self.assertNotIn("user_agent", options)
        self.assertEqual(options["service_workers"], "block")
        self.assertIn("--renderer-process-limit=2", arguments)

    def test_cloudflare_pending_becomes_manual_action(self):
        reason = (
            "La validación de seguridad de Cloudflare quedó pendiente "
            "en Chromium"
        )
        action = manual_action_for_reason(reason, enabled=True)
        self.assertIn("descarga manual", action)
        self.assertIsNone(
            manual_action_for_reason(reason, enabled=False)
        )

    def test_execution_summary_distinguishes_manual_and_errors(self):
        base = {
            "messages_failed": 0,
            "messages_partial": 0,
            "messages_manual": 0,
        }
        self.assertEqual(execution_status(base), "OK")
        self.assertEqual(
            execution_status({**base, "messages_manual": 1}),
            "REQUIERE_ATENCION_MANUAL",
        )
        self.assertEqual(
            execution_status({**base, "messages_failed": 1}),
            "COMPLETADO_CON_ERRORES",
        )



if __name__ == "__main__":
    unittest.main()
