import hashlib

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.config import Config


def _escape_query_value(value):
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


def _source_file_key(filename):
    return hashlib.sha256(filename.encode("utf-8")).hexdigest()[:32]


class DriveClient:
    def __init__(self, credentials):
        self.service = build("drive", "v3", credentials=credentials, cache_discovery=False)

    def find_existing(self, message_id, filename):
        message_id = _escape_query_value(message_id)
        source_file_key = _escape_query_value(_source_file_key(filename))
        folder_id = _escape_query_value(Config.drive_folder_id)
        query = (
            f"'{folder_id}' in parents and trashed = false and "
            f"appProperties has {{ key='gmailMessageId' and value='{message_id}' }} and "
            f"appProperties has {{ key='sourceFileKey' and value='{source_file_key}' }}"
        )
        response = self.service.files().list(
            q=query,
            pageSize=1,
            fields="files(id,name,webViewLink)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute(num_retries=Config.upload_retries)
        files = response.get("files", [])
        return files[0] if files else None

    def upload_file(self, path, message_id):
        existing = self.find_existing(message_id, path.name)
        if existing:
            print(
                f"[DRIVE] Ya existía para este correo: "
                f"{existing.get('name', path.name)}"
            )
            return {
                "id": existing["id"],
                "name": existing.get("name", path.name),
                "webViewLink": existing.get("webViewLink"),
                "skipped": True,
            }

        media = MediaFileUpload(
            str(path),
            chunksize=Config.upload_chunk_size_bytes(),
            resumable=True,
        )
        request = self.service.files().create(
            body={
                "name": path.name,
                "parents": [Config.drive_folder_id],
                "appProperties": {
                    "gmailMessageId": str(message_id),
                    "sourceFileKey": _source_file_key(path.name),
                },
            },
            media_body=media,
            fields="id,name,webViewLink",
            supportsAllDrives=True,
        )

        created = None
        last_reported = -1
        while created is None:
            status, created = request.next_chunk(num_retries=Config.upload_retries)
            if status:
                percent = int(status.progress() * 100)
                if percent >= last_reported + 10:
                    print(f"[DRIVE] Subiendo {path.name}: {percent}%")
                    last_reported = percent

        print(
            f"[DRIVE] Subido: {created.get('name')} "
            f"({created.get('webViewLink', created.get('id'))})"
        )
        created["skipped"] = False
        return created
