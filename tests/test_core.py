import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.browser_profile import (
    USER_AGENT,
    browser_context_options,
    browser_launch_arguments,
)
from app.browser_action_policy import (
    action_location_is_blocked,
    action_metadata_is_blocked,
)
from app.config import Config
from app.download_result import DownloadResult
from app.failure_policy import failure_is_permanent
from app.response_rules import (
    best_file_response,
    browser_file_response_score,
)
from app.link_policy import is_useful_email_link
from app.link_utils import canonical_link_key
from app.message_policy import is_provider_sender_confirmation
from app.provider_selectors import TRANSFERNOW_DOWNLOAD_SELECTORS
from app.status import execution_status, manual_action_for_reason
from app.retry_state import RetryState
from app.runtime import ExecutionLock
from app.utils import safe_filename, url_for_log


def load_filters():
    path = Path(__file__).parents[1] / "app" / "downloaders" / "filters.py"
    spec = importlib.util.spec_from_file_location("filters_standalone", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoreTests(unittest.TestCase):
    def test_wetransfer_ultimate_marketing_action_is_hard_blocked(self):
        metadata = {
            "tag": "a",
            "text": "Sé Ultimate",
            "href": "https://wetransfer.com/downloads/campaign/sign-up",
        }
        self.assertTrue(action_metadata_is_blocked(metadata))

    def test_account_and_upgrade_actions_are_never_download_candidates(self):
        for metadata in (
            {
                "tag": "button",
                "text": "Create your account",
                "href": "",
            },
            {
                "tag": "a",
                "text": "Download premium",
                "href": "https://example.com/upgrade",
            },
        ):
            self.assertTrue(action_metadata_is_blocked(metadata))

    def test_account_location_is_hard_blocked(self):
        self.assertTrue(
            action_location_is_blocked(
                "https://wetransfer.com/sign-up?from=downloads"
            )
        )

    def test_transfernow_download_all_anchor_has_first_priority(self):
        self.assertEqual(
            TRANSFERNOW_DOWNLOAD_SELECTORS[0],
            "a:text-is('Download all')",
        )
        self.assertLess(
            TRANSFERNOW_DOWNLOAD_SELECTORS.index(
                "a:has-text('Download all')"
            ),
            TRANSFERNOW_DOWNLOAD_SELECTORS.index(
                "[data-testid*='download' i]"
            ),
        )

    def test_real_download_all_action_remains_allowed(self):
        metadata = {
            "tag": "a",
            "text": "Download all",
            "href": "https://www.transfernow.net/download/transfer-123",
        }
        self.assertFalse(action_metadata_is_blocked(metadata))

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

    def test_security_alert_and_html_assets_are_not_download_links(self):
        for url in (
            "https://myaccount.google.com/security-checkup",
            "https://lh3.googleusercontent.com/mail-logo",
            "https://cdn.example.com/landing-page",
        ):
            self.assertFalse(
                is_useful_email_link(
                    url,
                    Config.allowed_extensions,
                )
            )

    def test_explicit_direct_file_link_is_kept(self):
        self.assertTrue(
            is_useful_email_link(
                "https://files.example.com/arte-final.zip",
                Config.allowed_extensions,
            )
        )
        self.assertTrue(
            is_useful_email_link(
                "https://files.example.com/get/123",
                Config.allowed_extensions,
                explicit_download=True,
            )
        )

    def test_tracking_and_cookie_images_are_not_file_responses(self):
        candidates = (
            (
                "https://tagging.wetransfer.com/download/pixel.png",
                {"content-type": "image/png"},
            ),
            (
                "https://cdn.cookielaw.org/logos/ot_guard_logo.svg",
                {"content-type": "image/svg+xml"},
            ),
        )
        for url, headers in candidates:
            self.assertIsNone(
                browser_file_response_score(
                    url,
                    headers,
                    "xhr",
                    Config.allowed_extensions,
                )
            )

    def test_attachment_response_is_a_strong_file_candidate(self):
        score = browser_file_response_score(
            "https://download.example.com/object/123",
            {
                "content-type": "application/octet-stream",
                "content-disposition": 'attachment; filename="arte.zip"',
            },
            "xhr",
            Config.allowed_extensions,
        )
        self.assertEqual(score, 100)

    def test_best_file_response_prefers_evidence_over_recency(self):
        selected = best_file_response(
            [
                {"url": "https://example.com/real.zip", "score": 100},
                {"url": "https://example.com/weak.bin", "score": 60},
            ]
        )
        self.assertEqual(
            selected["url"],
            "https://example.com/real.zip",
        )

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

    def test_retry_email_label_is_configured(self):
        self.assertEqual(
            Config.retry_label,
            "Descarga-Automatica-Reintento",
        )

    def test_transfernow_sender_confirmation_is_ignored(self):
        self.assertTrue(
            is_provider_sender_confirmation(
                "noreply@transfernow.net",
                "Sus archivos se han enviado con éxito a usuario@example.com",
            )
        )

    def test_transfernow_recipient_email_is_not_ignored(self):
        self.assertFalse(
            is_provider_sender_confirmation(
                "noreply@transfernow.net",
                'Alonso te envió "trabajo.zip" por TransferNow',
            )
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
        self.assertEqual(
            execution_status({**base, "messages_retry_pending": 1}),
            "REINTENTOS_PENDIENTES",
        )

    def test_retry_state_is_persistent_and_can_be_cleared(self):
        with TemporaryDirectory() as directory:
            first = RetryState(Path(directory))
            self.assertEqual(first.increment("mensaje-1"), 1)
            self.assertEqual(first.increment("mensaje-1"), 2)

            second = RetryState(Path(directory))
            self.assertEqual(second.count("mensaje-1"), 2)
            second.clear("mensaje-1")
            self.assertEqual(second.count("mensaje-1"), 0)

    def test_execution_lock_rejects_a_second_worker(self):
        with TemporaryDirectory() as directory:
            lock_path = Path(directory) / "worker.lock"
            with ExecutionLock(lock_path) as first:
                self.assertTrue(first)
                with ExecutionLock(lock_path) as second:
                    self.assertFalse(second)

    def test_expired_provider_link_is_a_permanent_failure(self):
        self.assertTrue(
            failure_is_permanent(
                ["El proveedor informa que el enlace está caducado"]
            )
        )
        self.assertFalse(
            failure_is_permanent(
                ["La interfaz dinámica todavía no está disponible"]
            )
        )



if __name__ == "__main__":
    unittest.main()
