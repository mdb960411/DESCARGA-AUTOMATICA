#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Ejecuta este instalador con sudo" >&2
    exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

install -d -m 0755 /etc/gmail-downloader
install -d -m 0755 /var/lib/gmail-downloader/downloads
install -d -m 0755 /var/lib/gmail-downloader/chrome-profile
install -d -m 0755 /var/lib/gmail-downloader/state
install -m 0755 "$script_dir/run-worker.sh" \
    /usr/local/bin/gmail-downloader-run
install -m 0644 "$script_dir/gmail-downloader.service" \
    /etc/systemd/system/gmail-downloader.service
install -m 0644 "$script_dir/gmail-downloader.timer" \
    /etc/systemd/system/gmail-downloader.timer

if [[ ! -f /etc/gmail-downloader/worker.env ]]; then
    install -m 0600 "$script_dir/worker.env.example" \
        /etc/gmail-downloader/worker.env
    echo "Se creó /etc/gmail-downloader/worker.env"
else
    echo "Se conservó la configuración existente de worker.env"
fi

systemctl daemon-reload
echo "Instalación preparada. Configura worker.env antes de iniciar el servicio."
