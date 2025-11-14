#!/bin/sh
set -e

# Genera env.js en base a la variable de entorno API_BASE_URL

ENV_JS_DIR=$(dirname "$ENV_JS_PATH")
mkdir -p "$ENV_JS_DIR"

cat <<EOF > "$ENV_JS_PATH"
window.__env = window.__env || {};
window.__env.apiBase = "${API_BASE_URL}";
EOF

echo "env.js generado en $ENV_JS_PATH con API_BASE_URL=${API_BASE_URL}"

# Arrancamos Nginx en foreground
nginx -g "daemon off;"
