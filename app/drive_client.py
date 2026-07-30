from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.config import Config
from app.idempotency import (
    find_content_duplicate,
    source_file_key,
)


def _escape_query_value(value):
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


class DriveClient:
    def __init__(self, credentials):
        self.service = build("drive", "v3", credentials=credentials, cache_discovery=False)

    def _list_files(self, query, page_size=1):
        response = self.service.files().list(
            q=query,
            pageSize=page_size,
            fields=(
                "files(id,name,webViewLink,size,md5Checksum,"
                "appProperties)"
            ),
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute(num_retries=Config.upload_retries)
        return response.get("files", [])

    def _annotate_existing(
        self,
        existing,
        message_id,
        source_file_key,
        source_transfer_key=None,
    ):
        properties = dict(existing.get("appProperties") or {})
        properties.setdefault("gmailMessageId", str(message_id))
        properties["lastGmailMessageId"] = str(message_id)
        properties["sourceFileKey"] = source_file_key
        if source_transfer_key:
            properties["sourceTransferKey"] = source_transfer_key

        updated = self.service.files().update(
            fileId=existing["id"],
            body={"appProperties": properties},
            fields=(
                "id,name,webViewLink,size,md5Checksum,appProperties"
            ),
            supportsAllDrives=True,
        ).execute(num_retries=Config.upload_retries)
        return {**existing, **updated}

    def find_existing(
        self,
        path,
        message_id,
        source_transfer_key=None,
    ):
        path = Path(path)
        escaped_message_id = _escape_query_value(message_id)
        file_key = source_file_key(path.name)
        escaped_source_file_key = _escape_query_value(file_key)
        folder_id = _escape_query_value(Config.drive_folder_id)
        base_query = f"'{folder_id}' in parents and trashed = false"

        provenance_queries = []
        if source_transfer_key:
            escaped_transfer_key = _escape_query_value(
                source_transfer_key
            )
            provenance_queries.append(
                f"{base_query} and "
                "appProperties has { "
                "key='sourceTransferKey' and "
                f"value='{escaped_transfer_key}' }} and "
                "appProperties has { "
                "key='sourceFileKey' and "
                f"value='{escaped_source_file_key}' }}"
            )

        provenance_queries.append(
            f"{base_query} and "
            "appProperties has { "
            "key='gmailMessageId' and "
            f"value='{escaped_message_id}' }} and "
            "appProperties has { "
            "key='sourceFileKey' and "
            f"value='{escaped_source_file_key}' }}"
        )

        for query in provenance_queries:
            files = self._list_files(query)
            if files:
                return self._annotate_existing(
                    files[0],
                    message_id,
                    file_key,
                    source_transfer_key,
                )

        # Compatibilidad con archivos subidos por V4.4, que todavía no tenían
        # sourceTransferKey. Solo se considera duplicado si nombre, tamaño y
        # MD5 coinciden; un trabajo nuevo con el mismo nombre no se descarta.
        escaped_name = _escape_query_value(path.name)
        same_name = self._list_files(
            f"{base_query} and name = '{escaped_name}'",
            page_size=100,
        )
        candidate = find_content_duplicate(path, same_name)
        if candidate is None:
            return None

        print(
            f"[DRIVE] Duplicado confirmado por contenido: "
            f"{path.name}"
        )
        return self._annotate_existing(
            candidate,
            message_id,
            file_key,
            source_transfer_key,
        )

    def upload_file(
        self,
        path,
        message_id,
        source_transfer_key=None,
    ):
        path = Path(path)
        existing = self.find_existing(
            path,
            message_id,
            source_transfer_key=source_transfer_key,
        )
        if existing:
            print(
                f"[DRIVE] Ya existía; no se volverá a subir: "
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
        app_properties = {
            "gmailMessageId": str(message_id),
            "sourceFileKey": source_file_key(path.name),
        }
        if source_transfer_key:
            app_properties["sourceTransferKey"] = source_transfer_key

        request = self.service.files().create(
            body={
                "name": path.name,
                "parents": [Config.drive_folder_id],
                "appProperties": app_properties,
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
