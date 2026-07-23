import json
import shutil
from datetime import datetime, timezone

from app.config import Config
from app.downloaders import download_url
from app.downloaders.filters import should_ignore_url
from app.drive_client import DriveClient
from app.gmail_client import GmailClient
from app.google_auth import get_credentials
from app.utils import safe_filename


def message_folder(base, index, sender, subject):
    folder = (
        base
        / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        / f"{index:03d}_{safe_filename(sender)[:60]}_{safe_filename(subject)[:80]}"
    )
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def run():
    print("VERSION_APP: V3-MODULAR-2026-07-23-02-SWISSTRANSFER")
    Config.validate()
    Config.download_dir.mkdir(parents=True, exist_ok=True)

    credentials = get_credentials()
    gmail = GmailClient(credentials)
    drive = DriveClient(credentials)

    message_ids = gmail.list_message_ids()
    print(f"Mensajes encontrados: {len(message_ids)}")
    summary = {
        "messages_found": len(message_ids),
        "messages_processed": 0,
        "files_uploaded": 0,
        "errors": [],
    }

    for index, message_id in enumerate(message_ids, 1):
        try:
            message = gmail.get_message(message_id)
            sender = gmail.sender_email(message)
            subject = gmail.subject(message)
            print(f"[CORREO] {sender} | {subject}")

            if not gmail.matches_rules(message):
                print("[CORREO] Omitido por reglas")
                continue

            folder = message_folder(Config.download_dir, index, sender, subject)
            downloaded = gmail.save_attachments(message_id, message, folder)
            links = gmail.extract_links(message)
            print(f"[CORREO] Enlaces útiles detectados: {len(links)}")

            for url in links:
                ignore, reason = should_ignore_url(url)

                if ignore:
                    print(f"[IGNORADO] {reason}: {url}")
                    continue

                path = download_url(url, folder)

                if path:
                    downloaded.append(path)

            if not downloaded:
                print("[CORREO] Sin archivos descargados; correo pendiente")
                continue

            for path in downloaded:
                drive.upload_file(path)

            gmail.mark_processed(message_id)
            summary["messages_processed"] += 1
            summary["files_uploaded"] += len(downloaded)
        except Exception as exc:
            error = f"Mensaje {message_id}: {exc}"
            print(error)
            summary["errors"].append(error)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main():
    try:
        run()
    finally:
        shutil.rmtree(Config.download_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
