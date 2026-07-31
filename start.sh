#!/bin/sh
set -eu

XVFB_DISPLAY_FILE="$(mktemp /tmp/xvfb-display.XXXXXX)"
XVFB_PID=""
APP_PID=""

cleanup() {
    if [ -n "$APP_PID" ] && kill -0 "$APP_PID" 2>/dev/null; then
        kill -TERM "$APP_PID" 2>/dev/null || true
        wait "$APP_PID" 2>/dev/null || true
    fi
    if [ -n "$XVFB_PID" ] && kill -0 "$XVFB_PID" 2>/dev/null; then
        kill -TERM "$XVFB_PID" 2>/dev/null || true
        wait "$XVFB_PID" 2>/dev/null || true
    fi
    rm -f "$XVFB_DISPLAY_FILE"
}

stop_container() {
    echo "[INICIO] Señal de detención recibida"
    cleanup
    exit 143
}

trap cleanup EXIT
trap stop_container INT TERM

echo "[INICIO] Iniciando pantalla virtual Xvfb"
Xvfb \
    -displayfd 3 \
    -screen 0 1280x800x24 \
    -nolisten tcp \
    -ac \
    3>"$XVFB_DISPLAY_FILE" \
    2>&1 &
XVFB_PID=$!

STARTUP_CHECK=0
while [ ! -s "$XVFB_DISPLAY_FILE" ]; do
    if ! kill -0 "$XVFB_PID" 2>/dev/null; then
        wait "$XVFB_PID" 2>/dev/null || true
        echo "[INICIO] ERROR: Xvfb terminó antes de crear la pantalla virtual"
        exit 1
    fi

    STARTUP_CHECK=$((STARTUP_CHECK + 1))
    if [ "$STARTUP_CHECK" -ge 100 ]; then
        echo "[INICIO] ERROR: Xvfb no respondió dentro de 10 segundos"
        exit 1
    fi
    sleep 0.1
done

DISPLAY_NUMBER="$(tr -dc '0-9' < "$XVFB_DISPLAY_FILE")"
if [ -z "$DISPLAY_NUMBER" ]; then
    echo "[INICIO] ERROR: Xvfb no informó un número de pantalla válido"
    exit 1
fi

export DISPLAY=":$DISPLAY_NUMBER"
echo "[INICIO] Pantalla virtual lista en DISPLAY=$DISPLAY"
echo "[INICIO] Iniciando aplicación Python"

python -m app.main &
APP_PID=$!

set +e
wait "$APP_PID"
APP_STATUS=$?
set -e
APP_PID=""

exit "$APP_STATUS"
