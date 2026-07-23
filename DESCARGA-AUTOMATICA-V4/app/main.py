import json
import shutil
from datetime import datetime, timezone
from uuid import uuid4

from app.config import Config
from app.downloaders import download_url
from app.downloaders.filters import should_ignore_url
from app.downloaders.manager import provider_for
from app.drive_client import DriveClient
from app.gmail_client import GmailClient
from app.google_auth import get_credentials
from app.utils import safe_error_message, safe_filename, url_for_log


def message_folder(base, index, sender, subject):
    folder = (
        base
        / f"{index:03d}_{safe_filename(sender)[:60]}_{safe_filename(subject)[:80]}"
    )
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def create_execution_folder():
    Config.download_dir.mkdir(parents=True, exist_ok=True)
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
    print("VERSION_APP: V4-GRAPHIC-LARGE-FILES-2026-07-23")
    Config.validate()
    execution_folder = create_execution_folder()
    summary = {
        "messages_found": 0,
        "messages_processed": 0,
        "messages_partial": 0,
        "messages_failed": 0,
        "files_downloaded": 0,
        "files_uploaded": 0,
        "files_skipped_duplicate": 0,
        "links_failed": 0,
        "errors": [],
    }

    try:
        credentials = get_credentials()
        gmail = GmailClient(credentials)
        drive = DriveClient(credentials)
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
                    print("[CORREO] Omitido por reglas")
                    continue

                folder = message_folder(
                    execution_folder, index, sender, subject
                )
                downloaded = gmail.save_attachments(
                    message_id, message, folder
                )
                links = gmail.extract_links(message)
                link_failures = []
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

                    attempted_links += 1
                    path = download_url(url, folder)

                    if path:
                        downloaded.append(path)
                    else:
                        failure = (
                            f"{provider_for(url)}:{url_for_log(url)}"
                        )
                        link_failures.append(failure)
                        summary["links_failed"] += 1

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

                if not downloaded and attempted_links == 0:
                    failures.append(
                        "El correo no contenía adjuntos o enlaces descargables"
                    )

                if failures:
                    partial = completed_files > 0
                    gmail.mark_failed(message_id, partial=partial)
                    status = "PARCIAL" if partial else "ERROR"
                    print(
                        f"[CORREO] Estado={status}. "
                        + " | ".join(failures)
                    )
                    if partial:
                        summary["messages_partial"] += 1
                    else:
                        summary["messages_failed"] += 1
                    summary["errors"].append(
                        f"Mensaje {message_id}: " + " | ".join(failures)
                    )
                    continue

                if completed_files == 0:
                    gmail.mark_failed(message_id, partial=False)
                    summary["messages_failed"] += 1
                    error = (
                        f"Mensaje {message_id}: no se completó ningún archivo"
                    )
                    print(f"[CORREO] Estado=ERROR. {error}")
                    summary["errors"].append(error)
                    continue

                gmail.mark_processed(message_id)
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

        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return summary
    finally:
        shutil.rmtree(execution_folder, ignore_errors=True)


def main():
    run()


if __name__ == "__main__":
    main()
