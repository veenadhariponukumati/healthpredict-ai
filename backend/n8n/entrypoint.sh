#!/bin/sh
set -e

# First-boot only: import and activate the bundled workflow definitions.
# n8n CLI commands bootstrap the DB schema/migrations on their own, so this
# is safe to run before the main process starts. Guarded by a marker file in
# the persistent volume so it only runs once, not on every container restart.
MARKER=/home/node/.n8n/.workflows-imported

if [ ! -f "$MARKER" ]; then
  echo "[init] Importing bundled workflows..."
  n8n import:workflow --separate --input=/home/node/.n8n/workflows
  n8n update:workflow --all --active=true
  touch "$MARKER"
  echo "[init] Workflows imported and activated."
fi

exec n8n
