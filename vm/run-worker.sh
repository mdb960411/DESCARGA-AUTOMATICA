#!/usr/bin/env bash
set -Eeuo pipefail

ENV_FILE="${GMAIL_DOWNLOADER_ENV_FILE:-/etc/gmail-downloader/worker.env}"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "No existe el archivo de configuración: $ENV_FILE" >&2
    exit 1
fi

set -a
# El archivo pertenece a root y solo contiene pares NOMBRE=VALOR.
source "$ENV_FILE"
set +a

required=(
    PROJECT_ID REGION AR_REPOSITORY IMAGE_NAME IMAGE_TAG
    CLIENT_SECRET_NAME OAUTH_TOKEN_SECRET_NAME DRIVE_FOLDER_ID
)
for name in "${required[@]}"; do
    if [[ -z "${!name:-}" ]]; then
        echo "Falta la variable obligatoria $name en $ENV_FILE" >&2
        exit 1
    fi
done

if [[ "$DRIVE_FOLDER_ID" == REEMPLAZAR_* ]]; then
    echo "Debes configurar DRIVE_FOLDER_ID en $ENV_FILE" >&2
    exit 1
fi

install -d -m 0755 /var/lib/gmail-downloader/downloads
install -d -m 0755 /var/lib/gmail-downloader/chrome-profile
install -d -m 0755 /var/lib/gmail-downloader/state

secret_dir="$(mktemp -d /run/gmail-downloader.XXXXXX)"
cleanup() {
    rm -f -- "$secret_dir/oauth-token.json"
    rm -f -- "$secret_dir/client-secret.json"
    rmdir -- "$secret_dir" 2>/dev/null || true
}
trap cleanup EXIT
umask 077

gcloud secrets versions access latest \
    --project="$PROJECT_ID" \
    --secret="$OAUTH_TOKEN_SECRET_NAME" \
    > "$secret_dir/oauth-token.json"
gcloud secrets versions access latest \
    --project="$PROJECT_ID" \
    --secret="$CLIENT_SECRET_NAME" \
    > "$secret_dir/client-secret.json"

registry="${REGION}-docker.pkg.dev"
image="${registry}/${PROJECT_ID}/${AR_REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}"
gcloud auth configure-docker "$registry" --quiet >/dev/null
docker pull "$image"

container_name="gmail-downloader-worker-$(date -u +%Y%m%dT%H%M%SZ)"
set +e
docker run --rm \
    --name "$container_name" \
    --init \
    --cpus=2 \
    --memory=3g \
    --shm-size=1g \
    --env-file "$ENV_FILE" \
    -e GOOGLE_OAUTH_TOKEN_FILE=/run/secrets/oauth-token.json \
    -e GOOGLE_CLIENT_SECRET_FILE=/run/secrets/client-secret.json \
    -v /var/lib/gmail-downloader/downloads:/data/downloads \
    -v /var/lib/gmail-downloader/chrome-profile:/data/chrome-profile \
    -v /var/lib/gmail-downloader/state:/data/state \
    -v "$secret_dir/oauth-token.json:/run/secrets/oauth-token.json:ro" \
    -v "$secret_dir/client-secret.json:/run/secrets/client-secret.json:ro" \
    "$image"
worker_status=$?
set -e

if [[ "${AUTO_SHUTDOWN:-false}" == "true" ]]; then
    echo "Ejecución terminada; la VM se apagará para reducir costos"
    shutdown -h now
fi

exit "$worker_status"
