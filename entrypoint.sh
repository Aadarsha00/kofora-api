#!/bin/sh
set -e

echo "Waiting for database..."
python << 'PYEOF'
import os, sys, time, urllib.parse
import socket

url = os.getenv("DATABASE_URL", "")
if url:
    parsed = urllib.parse.urlparse(url)
    host, port = parsed.hostname, parsed.port or 5432
    for i in range(30):
        try:
            socket.create_connection((host, port), timeout=2)
            print("Database is up.")
            sys.exit(0)
        except OSError:
            print(f"Waiting for {host}:{port}... ({i+1}/30)")
            time.sleep(2)
    print("Database never became available.")
    sys.exit(1)
PYEOF

exec "$@"
