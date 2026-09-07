#!/usr/bin/env bash
set -e

# Start a virtual X display so camoufox can run "headed" (fixes Docker crash).
Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp &
sleep 2

export DISPLAY=:99

# Launch the API server.
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"
