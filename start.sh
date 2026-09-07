#!/usr/bin/env bash
set -e

# Cap file-descriptor limit to a value we're actually allowed to set.
# (dbus/firefox try to raise it to 65536 and hang on Cloud Run gen2.)
ulimit -n 8192 || true

# Start a virtual X display so camoufox can run "headed" (fixes Docker crash).
Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp &
sleep 2
export DISPLAY=:99

# Start a private DBus session bus so Firefox doesn't hang waiting for one.
export $(dbus-launch)

# Launch the API server.
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"
