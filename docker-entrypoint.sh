#!/usr/bin/env bash
# Uygulama başlamadan önce DB migration'larını uygular.
# Böylece container her ayağa kalktığında şema güncel olur (create_all yok).
set -euo pipefail

echo "[entrypoint] Alembic migration uygulanıyor..."
alembic upgrade head

echo "[entrypoint] Uygulama başlatılıyor: $*"
exec "$@"
