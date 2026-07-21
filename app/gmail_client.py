from email.utils import parseaddr
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from app.config import Config
from app.utils import decode_base64url, extension_allowed, safe_filename, unique_path

class GmailClient:
    def __init__(self, credentials):
        self.service = build("gmail", "v1", credentials=credentials, cache_discovery=False)

    def list_message_ids(self):
        r = self.service.users().messages().list(userId="me", q=Config.gmail_query, maxResults=Config.max_emails).execute()
        return [x["id"] for x in r.get("messages", [])]

    def get_message(self, message_id):
        return self.service.users().messages().get(userId="me", id=message_id, format="full").execute()

    @staticmethod
    def headers(message):
        return {h.get("name", "").lower(): h.get("value", "") for h in message.get("payload", {}).get("headers", [])}

    @classmethod
    def sender_email(cls, message):
        return parseaddr(cls.headers(message).get("from", ""))[1].lower()

    @classmethod
    def subject(cls, message):
        return cls.headers(message).get("subject", "Sin asunto")

    @classmethod
    def walk_parts(cls, payload):
        yield payload
        for part in payload.get("parts", []) or []:
            yield from cls.walk_parts(part)

    def extract_body(self, message):
        text, html = [], []
        for part in self.walk_parts(message.get("payload", {})):
            mime = part.get("mimeType", "")
            data = part.get("body", {}).get("data")
            if not data:
                continue
            decoded = decode_base64url(data).decode("utf-8", errors="replace")
            if mime == "text/plain": text.append(decoded)
            elif mime == "text/html": html.append(decoded)
        return "\n".join(text), "\n".join(html)

    def matches_rules(self, message):
        sender = self.sender_email(message)
        if Config.only_from and sender != Config.only_from: return False
        if Config.only_from_domain and not sender.endswith(Config.only_from_domain): return False
        if Config.keyword:
            text, html = self.extract_body(message)
            combined = f"{self.subject(message)}\n{text}\n{BeautifulSoup(html, 'html.parser').get_text(' ')}".lower()
            if Config.keyword not in combined: return False
        return True

    def extract_links(self, message):
    import html as html_module
    import re
    from urllib.parse import urlsplit, urlunsplit

    text, html_body = self.extract_body(message)
    links = set()

    def clean_url(raw_url):
        if not raw_url:
            return None

        url = html_module.unescape(raw_url).strip()

        # Elimina caracteres habituales que quedan pegados al enlace
        # en correos en texto plano o con formato Markdown.
        url = url.strip(' \t\r\n<>"\'')
        url = url.rstrip(").,;:!?]}")

        # Algunos correos rodean los enlaces con __texto__.
        # Solo eliminamos guiones bajos ubicados al final de la URL.
        url = re.sub(r"_+$", "", url)

        if not url.lower().startswith(("http://", "https://")):
            return None

        try:
            parts = urlsplit(url)

            if not parts.netloc:
                return None

            # Protección adicional para dominios deformados.
            hostname = (parts.hostname or "").rstrip("_")

            if not hostname or "." not in hostname:
                return None

            netloc = hostname

            if parts.port:
                netloc = f"{netloc}:{parts.port}"

            url = urlunsplit(
                (
                    parts.scheme,
                    netloc,
                    parts.path,
                    parts.query,
                    parts.fragment,
                )
            )

            return url

        except Exception:
            return None

    # Enlaces reales incluidos en botones o texto HTML.
    if html_body:
        soup = BeautifulSoup(html_body, "html.parser")

        for anchor in soup.find_all("a", href=True):
            cleaned = clean_url(anchor.get("href"))

            if cleaned:
                links.add(cleaned)

    # Enlaces visibles dentro del cuerpo de texto.
    for match in re.findall(r'https?://[^\s<>"]+', text or "", re.I):
        cleaned = clean_url(match)

        if cleaned:
            links.add(cleaned)

    return sorted(links)

    def save_attachments(self, message_id, message, target_dir):
        saved = []
        for part in self.walk_parts(message.get("payload", {})):
            filename = part.get("filename")
            if not filename: continue
            filename = safe_filename(filename)
            if not extension_allowed(filename, Config.allowed_extensions): continue
            body = part.get("body", {})
            if body.get("data"):
                content = decode_base64url(body["data"])
            elif body.get("attachmentId"):
                a = self.service.users().messages().attachments().get(userId="me", messageId=message_id, id=body["attachmentId"]).execute()
                content = decode_base64url(a["data"])
            else:
                continue
            destination = unique_path(target_dir / filename)
            destination.write_bytes(content)
            saved.append(destination)
            print(f"Adjunto guardado: {destination}")
        return saved

    def get_or_create_label(self, name):
        labels = self.service.users().labels().list(userId="me").execute().get("labels", [])
        for label in labels:
            if label.get("name", "").lower() == name.lower(): return label["id"]
        return self.service.users().labels().create(userId="me", body={"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}).execute()["id"]

    def mark_processed(self, message_id):
        body = {"addLabelIds": [self.get_or_create_label(Config.processed_label)]}
        if Config.mark_as_read: body["removeLabelIds"] = ["UNREAD"]
        self.service.users().messages().modify(userId="me", id=message_id, body=body).execute()
