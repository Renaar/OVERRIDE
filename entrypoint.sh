#!/bin/sh
# Started as root only to fix ownership of the data volume (Docker creates ./data as root),
# then the app runs as the unprivileged user "override" (uid 1000).
set -e
if [ "$(id -u)" = "0" ]; then
  mkdir -p "$DATA_DIR"
  chown -R override:override "$DATA_DIR"
  exec setpriv --reuid=override --regid=override --init-groups "$@"
fi
exec "$@"
