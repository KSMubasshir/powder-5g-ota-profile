#!/bin/bash
# Query the modem on its dedicated AT interface, without changing its settings.
set -euo pipefail
source "$(dirname "$0")/setup-common.sh"
setup_begin ue-status refresh
if [[ $# -gt 1 ]]; then
    echo "usage: $0 [/dev/AT_PORT]" >&2
    exit 2
fi
port=${1:-}
if [[ -z $port ]]; then
    candidates=()
    for candidate in /dev/ttyUSB*; do
        [[ -c $candidate ]] || continue
        props=$(udevadm info --query=property --name="$candidate")
        if grep -qiE 'Quectel|RM5[0-9]' <<< "$props" &&
           grep -q '^ID_USB_INTERFACE_NUM=02$' <<< "$props"; then
            candidates+=("$candidate")
        fi
    done
    if [[ ${#candidates[@]} -ne 1 ]]; then
        echo 'Could not identify exactly one modem AT interface; supply its device path.' >&2
        exit 1
    fi
    port=${candidates[0]}
fi
systemctl --no-pager status quectel-cm.service || true
python3 - "$port" <<'PY'
import fcntl
import os
import select
import sys
import termios
import time

fd = os.open(sys.argv[1], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    old = termios.tcgetattr(fd)
    new = termios.tcgetattr(fd)
    new[0] = new[1] = new[3] = 0
    new[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    new[4] = new[5] = termios.B115200
    new[6][termios.VMIN] = 0
    new[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, new)
    try:
        for command in ('ATI', 'AT+CIMI', 'AT+QENG="servingcell"', 'AT+QNWINFO'):
            print(command, flush=True)
            os.write(fd, (command + '\r').encode('ascii'))
            deadline = time.monotonic() + 3
            response = b''
            while time.monotonic() < deadline:
                ready, _, _ = select.select([fd], [], [], max(0, deadline - time.monotonic()))
                if not ready:
                    break
                chunk = os.read(fd, 4096)
                if not chunk:
                    break
                response += chunk
                if b'\r\nOK\r\n' in response or b'\r\nERROR\r\n' in response:
                    break
            print(response.decode('ascii', errors='replace'), flush=True)
            if not response:
                raise RuntimeError('No modem response')
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, old)
finally:
    os.close(fd)
PY
setup_complete
