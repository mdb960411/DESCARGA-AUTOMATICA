from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = ["https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/drive.file"]
if __name__ == "__main__":
    if not Path("credentials.json").exists(): raise SystemExit("Falta credentials.json")
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    Path("token.json").write_text(creds.to_json(), encoding="utf-8")
    print("token.json generado")
