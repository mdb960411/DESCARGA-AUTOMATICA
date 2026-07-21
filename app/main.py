import json, shutil
from datetime import datetime, timezone
from app.config import Config
from app.downloaders import download_url
from app.drive_client import DriveClient
from app.gmail_client import GmailClient
from app.google_auth import get_credentials
from app.utils import safe_filename

def message_folder(base, index, sender, subject):
    folder = base / datetime.now(timezone.utc).strftime("%Y-%m-%d") / f"{index:03d}_{safe_filename(sender)[:60]}_{safe_filename(subject)[:80]}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder

def run():
    Config.validate(); Config.download_dir.mkdir(parents=True, exist_ok=True)
    creds = get_credentials(); gmail = GmailClient(creds); drive = DriveClient(creds)
    ids = gmail.list_message_ids(); print(f"Mensajes encontrados: {len(ids)}")
    summary = {"messages_found": len(ids), "messages_processed": 0, "files_uploaded": 0, "errors": []}
    for index, message_id in enumerate(ids, 1):
        try:
            message = gmail.get_message(message_id)
            sender, subject = gmail.sender_email(message), gmail.subject(message)
            if not gmail.matches_rules(message):
                print(f"Omitido por reglas: {sender} | {subject}"); continue
            folder = message_folder(Config.download_dir, index, sender, subject)
            downloaded = gmail.save_attachments(message_id, message, folder)
            for url in gmail.extract_links(message):
                print(f"LINK DETECTADO -> {repr(url)}")
                path = download_url(url, folder)
                if path: downloaded.append(path)
            if not downloaded:
                print("Sin archivos; correo pendiente"); continue
            for path in downloaded: drive.upload_file(path)
            gmail.mark_processed(message_id)
            summary["messages_processed"] += 1; summary["files_uploaded"] += len(downloaded)
        except Exception as exc:
            error = f"Mensaje {message_id}: {exc}"; print(error); summary["errors"].append(error)
    print(json.dumps(summary, ensure_ascii=False, indent=2)); return summary

def main():
    try: run()
    finally: shutil.rmtree(Config.download_dir, ignore_errors=True)

if __name__ == "__main__": main()
