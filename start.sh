#!/usr/bin/env bash
set -e

# Start a virtual X display so camoufox can run "headed" (fixes Docker crash).
Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp &
sleep 2
export DISPLAY=:99

# Do NOT start a real dbus session. dbus-launch tries to raise the fd limit to
# 65536, which Cloud Run's sandbox refuses, and Firefox then hangs forever.
# Pointing the bus address at a dead socket makes Firefox skip dbus cleanly.
export DBUS_SESSION_BUS_ADDRESS=/dev/null

# Launch the API server.
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"
