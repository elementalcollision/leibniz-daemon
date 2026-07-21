#!/bin/zsh
# ADR 0068 — install (or refresh) the nightly heartbeat LaunchAgent. OPERATOR-RUN (or operator-
# sanctioned): this creates standing scheduled execution with capped LLM spend. To disable:
#   launchctl bootout gui/$(id -u)/com.elementalcollision.leibniz.heartbeat
set -eu
HERE="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$HOME/.leibniz-heartbeat" "$HOME/Library/LaunchAgents"
cp "$HERE/deploy/heartbeat/launch-heartbeat.sh" "$HOME/.leibniz-heartbeat/launch.sh"
chmod +x "$HOME/.leibniz-heartbeat/launch.sh"
PLIST="$HOME/Library/LaunchAgents/com.elementalcollision.leibniz.heartbeat.plist"
cp "$HERE/deploy/heartbeat/com.elementalcollision.leibniz.heartbeat.plist" "$PLIST"
launchctl bootout "gui/$(id -u)/com.elementalcollision.leibniz.heartbeat" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "installed: nightly beat at 02:30 (label com.elementalcollision.leibniz.heartbeat)"
echo "manual beat:  $HOME/.leibniz-heartbeat/launch.sh"
echo "disable:      launchctl bootout gui/$(id -u)/com.elementalcollision.leibniz.heartbeat"
