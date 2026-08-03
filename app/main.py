import json
import shutil
from datetime import datetime, timezone
from uuid import uuid4

from app.config import Config
from app.downloaders import download_url
from app.downloaders.filters import should_ignore_url
from app.downloaders.manager import provider_for
from app.drive_client import DriveClient
from app.failure_policy import failure_is_permanent
from app.gmail_client import GmailClient
from app.google_auth import get_credentials
from app.retry_state import RetryState
from app.runtime import ExecutionLock, cleanup_stale_runs
from app.status import execution_status
from app.utils import safe_error_message, safe_filename, url_for_log

VERSION_APP = "V5.2-SAFE-ACTIONS-2026-08-03"


def message_folder(base, index, sender, subject):
    folder = (
        base
        / f"{index:03d}_{safe_filename(sender)[:60]}_{safe_filename(subject)[:80]}"
    )
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def create_execution_folder():
    Config.download_dir.mkdir(parents=True, exist_ok=True)
    removed = cleanup_stale_runs(
        Config.download_dir,
        Config.stale_run_hours,
    )
    if removed:
        print(
            f"[LIMPIEZA] Carpetas de ejecuciones interrumpidas eliminadas: "
            f"{removed}"
        )
    execution_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "_"
        + uuid4().hex[:8]
    )
    folder = Config.download_dir / f"run_{execution_id}"
    folder.mkdir(parents=True, exist_ok=False)

    # Prueba temprana de escritura. Si el volumen no está montado o carece de
    # permisos, el job falla antes de abrir Gmail o Chromium.
    probe = folder / ".storage-write-test"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
    return folder


def run():
    print(f"VERSION_APP: {VERSION_APP}")
    Config.validate()
    execution_folder = create_execution_folder()
    summary = {
        "messages_found": 0,
        "messages_processed": 0,
        "messages_ignored": 0,
        "messages_partial": 0,
        "messages_failed": 0,
        "messages_manual": 0,
        "messages_manual_partial": 0,
        "messages_retry_pending": 0,
        "messages_retry_partial": 0,
        "files_downloaded": 0,
        "files_uploaded": 0,
        "files_skipped_duplicate": 0,
        "links_failed": 0,
        "links_manual": 0,
        "execution_status": "EN_EJECUCION",
        "manual_actions": [],
        "retry_pending": [],
        "errors": [],
    }

    try:
        credentials = get_credentials()
        gmail = GmailClient(credentials)
        drive = DriveClient(credentials)
        retry_state = RetryState(Config.state_dir)
        gmail.ensure_status_labels()

        message_ids = gmail.list_message_ids()
        summary["messages_found"] = len(message_ids)
        print(f"Mensajes encontrados: {len(message_ids)}")

        for index, message_id in enumerate(message_ids, 1):
            folder = None
            completed_files = 0
            try:
                message = gmail.get_message(message_id)
                sender = gmail.sender_email(message)
                subject = gmail.subject(message)
                print(f"[CORREO] {sender} | {subject}")

                if not gmail.matches_rules(message):
                    gmail.mark_ignored(message_id)
                    retry_state.clear(message_id)
                    summary["messages_ignored"] += 1
                    print("[CORREO] Estado=IGNORADO. No cumple las reglas")
                    continue

                if gmail.is_provider_sender_confirmation(message):
                    gmail.mark_ignored(message_id)
                    retry_state.clear(message_id)
                    summary["messages_ignored"] += 1
                    print(
                        "[CORREO] Estado=IGNORADO. "
                        "Es una confirmación de envío y no una recepción"
                    )
                    continue

                folder = message_folder(
                    execution_folder, index, sender, subject
                )
                downloaded = gmail.save_attachments(
                    message_id, message, folder
                )
                links = gmail.extract_links(message)
                link_failures = []
                link_manual = []
                alternative_failures = {}
                alternative_manual = {}
                completed_alternative_providers = set()
                upload_failures = []
                attempted_links = 0
                print(f"[CORREO] Enlaces útiles detectados: {len(links)}")

                for url in links:
                    ignore, reason = should_ignore_url(url)

                    if ignore:
                        print(
                            f"[IGNORADO] {reason}: {url_for_log(url)}"
                        )
                        continue

                    provider = provider_for(url)
                    is_alternative = (
                        provider == "wetransfer"
                        and sender.endswith("@wetransfer.com")
                    )
                    if (
                        is_alternative
                        and provider in completed_alternative_providers
                    ):
                        print(
                            "[IGNORADO] Variante alternativa de "
                            "WeTransfer; la transferencia ya se completó"
                        )
                        continue

                    attempted_links += 1
                    result = download_url(url, folder)
                    downloaded.extend(result.paths)

                    failure = None
                    if result.errors:
                        normalized_errors = [
                            safe_error_message(error)
                            for error in result.errors
                        ]
                        visible_errors = normalized_errors[:5]
                        if len(normalized_errors) > len(visible_errors):
                            visible_errors.append(
                                f"{len(normalized_errors) - len(visible_errors)} "
                                "errores adicionales"
                            )
                        details = "; ".join(visible_errors)
                        failure = (
                            f"{provider}:{url_for_log(url)}"
                            f" ({details})"
                        )

                    manual_request = None
                    if result.manual_actions:
                        normalized_actions = [
                            safe_error_message(action)
                            for action in result.manual_actions
                        ]
                        details = "; ".join(normalized_actions[:5])
                        manual_request = (
                            f"{provider}:{url_for_log(url)}"
                            f" ({details})"
                        )

                    clean_success = (
                        bool(result.paths)
                        and not result.errors
                        and not result.manual_actions
                    )
                    if is_alternative and clean_success:
                        completed_alternative_providers.add(provider)
                        alternative_failures.pop(provider, None)
                        alternative_manual.pop(provider, None)
                    elif is_alternative:
                        if failure:
                            alternative_failures.setdefault(
                                provider,
                                [],
                            ).append(failure)
                        if manual_request:
                            alternative_manual.setdefault(
                                provider,
                                [],
                            ).append(manual_request)
                    else:
                        if failure:
                            link_failures.append(failure)
                            summary["links_failed"] += 1
                        if manual_request:
                            link_manual.append(manual_request)
                            summary["links_manual"] += 1

                for provider, failures_for_provider in (
                    alternative_failures.items()
                ):
                    if provider not in completed_alternative_providers:
                        link_failures.extend(failures_for_provider)
                        summary["links_failed"] += len(
                            failures_for_provider
                        )
                for provider, manual_for_provider in (
                    alternative_manual.items()
                ):
                    if provider not in completed_alternative_providers:
                        link_manual.extend(manual_for_provider)
                        summary["links_manual"] += len(
                            manual_for_provider
                        )

                summary["files_downloaded"] += len(downloaded)

                for path in downloaded:
                    try:
                        result = drive.upload_file(path, message_id)
                        completed_files += 1
                        if result.get("skipped"):
                            summary["files_skipped_duplicate"] += 1
                        else:
                            summary["files_uploaded"] += 1
                    except Exception as exc:
                        upload_failures.append(
                            f"{path.name}: {safe_error_message(exc)}"
                        )

                failures = [
                    *(f"Descarga fallida {item}" for item in link_failures),
                    *(f"Subida fallida {item}" for item in upload_failures),
                ]
                manual_requests = [
                    f"Intervención manual {item}"
                    for item in link_manual
                ]

                if not downloaded and attempted_links == 0:
                    gmail.mark_ignored(message_id)
                    retry_state.clear(message_id)
                    summary["messages_ignored"] += 1
                    print(
                        "[CORREO] Estado=IGNORADO. "
                        "No contiene adjuntos o enlaces descargables"
                    )
                    continue

                if failures:
                    partial = completed_files > 0
                    current_attempt = retry_state.increment(message_id)
                    permanent = failure_is_permanent(failures)
                    if (
                        not permanent
                        and current_attempt < Config.max_message_attempts
                    ):
                        gmail.mark_retry(message_id, partial=partial)
                        summary["messages_retry_pending"] += 1
                        if partial:
                            summary["messages_retry_partial"] += 1
                        pending = (
                            f"Mensaje {message_id}: intento programado "
                            f"{current_attempt + 1} de "
                            f"{Config.max_message_attempts}: "
                            + " | ".join(failures)
                        )
                        summary["retry_pending"].append(pending)
                        print(
                            "[CORREO] Estado=REINTENTO_PENDIENTE. "
                            f"Próxima ejecución "
                            f"{current_attempt + 1}/"
                            f"{Config.max_message_attempts}. "
                            + " | ".join(failures)
                        )
                        continue

                    retry_state.clear(message_id)
                    gmail.mark_failed(message_id, partial=partial)
                    status = "PARCIAL" if partial else "ERROR"
                    reason = (
                        "fallo permanente"
                        if permanent
                        else f"límite de {Config.max_message_attempts} intentos"
                    )
                    print(
                        f"[CORREO] Estado={status}. {reason}. "
                        + " | ".join(failures)
                    )
                    if partial:
                        summary["messages_partial"] += 1
                    else:
                        summary["messages_failed"] += 1
                    summary["errors"].append(
                        f"Mensaje {message_id}: " + " | ".join(failures)
                    )
                    if manual_requests:
                        summary["manual_actions"].append(
                            f"Mensaje {message_id}: "
                            + " | ".join(manual_requests)
                        )
                    continue

                if manual_requests:
                    retry_state.clear(message_id)
                    partial_manual = completed_files > 0
                    gmail.mark_manual(
                        message_id,
                        partial=partial_manual,
                    )
                    summary["messages_manual"] += 1
                    if partial_manual:
                        summary["messages_manual_partial"] += 1
                    summary["manual_actions"].append(
                        f"Mensaje {message_id}: "
                        + " | ".join(manual_requests)
                    )
                    status = (
                        "PARCIAL_MANUAL"
                        if partial_manual
                        else "MANUAL"
                    )
                    print(
                        f"[CORREO] Estado={status}. "
                        + " | ".join(manual_requests)
                    )
                    continue

                if completed_files == 0:
                    retry_state.clear(message_id)
                    gmail.mark_failed(message_id, partial=False)
                    summary["messages_failed"] += 1
                    error = (
                        f"Mensaje {message_id}: no se completó ningún archivo"
                    )
                    print(f"[CORREO] Estado=ERROR. {error}")
                    summary["errors"].append(error)
                    continue

                gmail.mark_processed(message_id)
                retry_state.clear(message_id)
                summary["messages_processed"] += 1
                print(
                    f"[CORREO] Estado=PROCESADO. "
                    f"Archivos completados={completed_files}"
                )
            except Exception as exc:
                error = (
                    f"Mensaje {message_id}: "
                    f"{safe_error_message(exc)}"
                )
                current_attempt = retry_state.increment(message_id)
                if current_attempt < Config.max_message_attempts:
                    try:
                        gmail.mark_retry(
                            message_id,
                            partial=completed_files > 0,
                        )
                    except Exception as label_exc:
                        print(
                            "[GMAIL] No se pudo etiquetar el reintento: "
                            f"{safe_error_message(label_exc)}"
                        )
                    summary["messages_retry_pending"] += 1
                    if completed_files > 0:
                        summary["messages_retry_partial"] += 1
                    summary["retry_pending"].append(
                        f"{error}; próxima ejecución "
                        f"{current_attempt + 1}/"
                        f"{Config.max_message_attempts}"
                    )
                    print(
                        "[CORREO] Estado=REINTENTO_PENDIENTE. "
                        f"Próxima ejecución {current_attempt + 1}/"
                        f"{Config.max_message_attempts}. {error}"
                    )
                    continue

                retry_state.clear(message_id)
                print(f"[CORREO] Estado=ERROR. {error}")
                summary["errors"].append(error)
                summary["messages_failed"] += 1
                try:
                    gmail.mark_failed(
                        message_id, partial=completed_files > 0
                    )
                except Exception as label_exc:
                    print(
                        "[GMAIL] No se pudo etiquetar el error: "
                        f"{safe_error_message(label_exc)}"
                    )
            finally:
                if folder is not None:
                    shutil.rmtree(folder, ignore_errors=True)

        summary["execution_status"] = execution_status(summary)
        print(
            f"[RESUMEN] Estado={summary['execution_status']} "
            f"procesados={summary['messages_processed']} "
            f"manuales={summary['messages_manual']} "
            f"reintentos={summary['messages_retry_pending']} "
            f"parciales={summary['messages_partial']} "
            f"errores={summary['messages_failed']} "
            f"ignorados={summary['messages_ignored']}"
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return summary
    finally:
        shutil.rmtree(execution_folder, ignore_errors=True)


def main():
    lock_path = Config.state_dir / "worker.lock"
    with ExecutionLock(lock_path) as acquired:
        if not acquired:
            summary = {
                "messages_found": 0,
                "messages_processed": 0,
                "messages_ignored": 0,
                "messages_partial": 0,
                "messages_failed": 0,
                "messages_manual": 0,
                "messages_manual_partial": 0,
                "messages_retry_pending": 0,
                "messages_retry_partial": 0,
                "files_downloaded": 0,
                "files_uploaded": 0,
                "files_skipped_duplicate": 0,
                "links_failed": 0,
                "links_manual": 0,
                "execution_status": "OMITIDA_EJECUCION_ACTIVA",
                "manual_actions": [],
                "retry_pending": [],
                "errors": [],
            }
            print(
                "[EJECUCION] Ya existe otra ejecución activa; "
                "esta ejecución finalizará sin procesar correos"
            )
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return summary
        return run()


if __name__ == "__main__":
    main()
