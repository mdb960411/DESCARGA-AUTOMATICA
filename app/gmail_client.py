import html as html_module
import re
from email.header import decode_header, make_header
from email.utils import parseaddr
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup
from googleapiclient.discovery import build

from app.config import Config
from app.link_utils import canonical_link_key
from app.utils import decode_base64url, extension_allowed, safe_filename, unique_path


class GmailClient:
    def __init__(self, credentials):
        self.service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        self._label_cache = None

    def list_message_ids(self):
        query = Config.gmail_query.strip()

        # Las exclusiones evitan reprocesar mensajes ya finalizados y detienen
        # ciclos infinitos sobre enlaces vencidos o incompatibles.
        excluded_labels = [Config.processed_label]
        if Config.exclude_error_messages:
            excluded_labels.append(Config.error_label)
        if Config.exclude_ignored_messages:
            excluded_labels.append(Config.ignored_label)

        normalized_query = query.lower()
        for label in excluded_labels:
            if label and label.lower() not in normalized_query:
                query = f'{query} -label:"{label}"'.strip()

        print(f"[GMAIL] Consulta activa: {query}")
        response = self.service.users().messages().list(
            userId="me",
            q=query,
            maxResults=Config.max_emails,
        ).execute()
        return [item["id"] for item in response.get("messages", [])]

    def get_message(self, message_id):
        return self.service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()

    @staticmethod
    def _decode_header_value(value):
        if not value:
            return ""
        try:
            return str(make_header(decode_header(value)))
        except Exception:
            return value

    @classmethod
    def headers(cls, message):
        result = {}
        for header in message.get("payload", {}).get("headers", []):
            name = header.get("name", "").lower()
            value = cls._decode_header_value(header.get("value", ""))
            result[name] = value
        return result

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
        text_parts = []
        html_parts = []

        for part in self.walk_parts(message.get("payload", {})):
            mime_type = (part.get("mimeType") or "").lower()
            data = part.get("body", {}).get("data")
            if not data:
                continue

            decoded = decode_base64url(data).decode("utf-8", errors="replace")
            if mime_type == "text/plain":
                text_parts.append(decoded)
            elif mime_type == "text/html":
                html_parts.append(decoded)

        return "\n".join(text_parts), "\n".join(html_parts)

    def matches_rules(self, message):
        sender = self.sender_email(message)
        if Config.only_from and sender != Config.only_from:
            return False
        if Config.only_from_domain and not sender.endswith(Config.only_from_domain):
            return False
        if Config.keyword:
            text, html_body = self.extract_body(message)
            combined = (
                f"{self.subject(message)}\n{text}\n"
                f"{BeautifulSoup(html_body, 'html.parser').get_text(' ')}"
            ).lower()
            if Config.keyword not in combined:
                return False
        return True

    @staticmethod
    def _clean_url(raw_url):
        if not raw_url:
            return None

        url = html_module.unescape(str(raw_url)).strip()
        url = url.strip(" \t\r\n<>\"'")
        url = url.rstrip(").,;:!?]}")

        if not url.lower().startswith(("http://", "https://")):
            return None

        try:
            parts = urlsplit(url)
        except ValueError:
            return None

        hostname = (parts.hostname or "").lower().strip()
        if not hostname or "." not in hostname:
            return None

        # Never repair malformed domains. They are decorative/broken links,
        # while the same email normally contains a valid transfer link.
        if re.search(r"[_-]+$", hostname):
            return None

        netloc = hostname
        if parts.port:
            netloc = f"{netloc}:{parts.port}"

        return urlunsplit((parts.scheme.lower(), netloc, parts.path, parts.query, parts.fragment))

    @staticmethod
    def _is_useful_link(url):
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        path = parts.path or "/"

        # Known transfer URLs: retain only links that identify a transfer.
        if host in {"we.tl"}:
            return path.startswith("/t-")
        if host.endswith("wetransfer.com"):
            return path.startswith("/downloads/")
        if host.endswith("sendgb.com"):
            blocked_prefixes = (
                "/images/",
                "/css/",
                "/js/",
                "/assets/",
            )
            return (
                path.strip("/") != ""
                and not path.lower().startswith(blocked_prefixes)
            )
        if host.endswith("sendallfiles.com"):
            return "/d/" in path
        if host.endswith("transfernow.net"):
            return path.startswith("/dl/")

        # Google Drive file links remain useful.
        if host == "drive.google.com":
            return any(token in url for token in ("/file/d/", "open?id=", "uc?"))

        # Skip common navigation/tracking links.
        blocked_hosts = {
            "g.co",
            "notifications.googleapis.com",
            "accounts.google.com",
            "support.google.com",
        }
        if host in blocked_hosts:
            return False

        blocked_path_terms = (
            "unsubscribe",
            "notification-settings",
            "help-center",
            "/legal/",
            "/terms",
            "/privacy",
            "user-reports",
            "/contact",
        )
        if any(term in path.lower() for term in blocked_path_terms):
            return False

        return True

    def extract_links(self, message):
        text, html_body = self.extract_body(message)
        candidates = []

        # Provider-specific headers can contain the most reliable download URL.
        headers = self.headers(message)
        for name in ("x-wt-download-url",):
            if headers.get(name):
                candidates.append(headers[name])

        if html_body:
            soup = BeautifulSoup(html_body, "html.parser")
            candidates.extend(
                anchor.get("href")
                for anchor in soup.find_all("a", href=True)
            )

        # Read visible URLs from both plain text and HTML as a fallback.
        for source in (text, html_body):
            candidates.extend(re.findall(r'https?://[^\s<>"\']+', source or "", re.I))

        links = set()
        for candidate in candidates:
            cleaned = self._clean_url(candidate)
            if cleaned and self._is_useful_link(cleaned):
                links.add(cleaned)

        # Prefiere las URL canónicas cortas y evita probar varias variantes del
        # mismo envío de WeTransfer.
        ordered_links = sorted(links, key=lambda item: (len(item), item))
        deduplicated = []
        seen_keys = set()
        for link in ordered_links:
            key = canonical_link_key(link)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduplicated.append(link)
        return deduplicated

    def save_attachments(self, message_id, message, target_dir):
        saved = []
        for part in self.walk_parts(message.get("payload", {})):
            filename = part.get("filename")
            if not filename:
                continue

            filename = safe_filename(filename)
            if not extension_allowed(filename, Config.allowed_extensions):
                continue

            body = part.get("body", {})
            if body.get("data"):
                content = decode_base64url(body["data"])
            elif body.get("attachmentId"):
                attachment = self.service.users().messages().attachments().get(
                    userId="me",
                    messageId=message_id,
                    id=body["attachmentId"],
                ).execute()
                content = decode_base64url(attachment["data"])
            else:
                continue

            destination = unique_path(target_dir / filename)
            destination.write_bytes(content)
            saved.append(destination)
            print(f"Adjunto guardado: {destination}")
        return saved

    def _load_label_cache(self, force=False):
        if self._label_cache is None or force:
            labels = (
                self.service.users()
                .labels()
                .list(userId="me")
                .execute()
                .get("labels", [])
            )
            self._label_cache = {
                label.get("name", "").lower(): label["id"]
                for label in labels
                if label.get("name") and label.get("id")
            }
        return self._label_cache

    def label_id(self, name, create=False):
        cache = self._load_label_cache()
        label_id = cache.get(name.lower())
        if label_id or not create:
            return label_id

        created = self.service.users().labels().create(
            userId="me",
            body={
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        ).execute()
        self._label_cache[name.lower()] = created["id"]
        return created["id"]

    def ensure_status_labels(self):
        for name in (
            Config.processed_label,
            Config.error_label,
            Config.partial_label,
            Config.ignored_label,
        ):
            self.label_id(name, create=True)

    def _modify_status(
        self,
        message_id,
        *,
        add_labels,
        remove_labels=(),
        mark_as_read=False,
    ):
        add_ids = [
            self.label_id(name, create=True)
            for name in add_labels
            if name
        ]
        remove_ids = [
            label_id
            for name in remove_labels
            if name
            for label_id in [self.label_id(name, create=False)]
            if label_id
        ]

        if mark_as_read:
            remove_ids.append("UNREAD")

        body = {"addLabelIds": list(dict.fromkeys(add_ids))}
        if remove_ids:
            body["removeLabelIds"] = list(dict.fromkeys(remove_ids))

        self.service.users().messages().modify(
            userId="me", id=message_id, body=body
        ).execute()

    def mark_processed(self, message_id):
        self._modify_status(
            message_id,
            add_labels=[Config.processed_label],
            remove_labels=[
                Config.error_label,
                Config.partial_label,
                Config.ignored_label,
            ],
            mark_as_read=Config.mark_as_read,
        )

    def mark_failed(self, message_id, partial=False):
        add_labels = [Config.error_label]
        if partial:
            add_labels.append(Config.partial_label)

        self._modify_status(
            message_id,
            add_labels=add_labels,
            remove_labels=[Config.processed_label, Config.ignored_label],
            mark_as_read=False,
        )

    def mark_ignored(self, message_id):
        self._modify_status(
            message_id,
            add_labels=[Config.ignored_label],
            remove_labels=[
                Config.processed_label,
                Config.error_label,
                Config.partial_label,
            ],
            # Un correo personal sin archivos no debe marcarse como leído por
            # una automatización destinada únicamente a transferencias.
            mark_as_read=False,
        )
