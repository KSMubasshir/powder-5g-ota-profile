#!/bin/bash
# Shared setup state; source this file, rather than executing it.
export DEBIAN_FRONTEND=noninteractive
SETUP_DIR=/local/setup
LOG_DIR=/local/logs
setup_begin() {
    local name=$1 mode=${2:-once}
    sudo mkdir -p "$SETUP_DIR" "$LOG_DIR"
    SETUP_MARKER="$SETUP_DIR/$name.complete"
    exec > >(sudo tee -a "$LOG_DIR/$name.log") 2>&1
    echo "$(date -u +%FT%TZ) $name"
    if [[ $mode == once && -f $SETUP_MARKER ]]; then
        echo "setup already completed"
        exit 0
    fi
}
setup_complete() {
    sudo touch "$SETUP_MARKER"
    echo "$(date -u +%FT%TZ) complete"
}
