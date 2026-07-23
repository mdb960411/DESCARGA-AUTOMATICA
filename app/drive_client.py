from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from app.config import Config

class DriveClient:
    def __init__(self, credentials):
        self.service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    def upload_file(self, path):
        created = self.service.files().create(body={"name": path.name, "parents": [Config.drive_folder_id]}, media_body=MediaFileUpload(str(path), resumable=True), fields="id,name,webViewLink", supportsAllDrives=True).execute()
        print(f"Subido a Drive: {created.get('name')} ({created.get('webViewLink', created.get('id'))})")
        return created["id"]
