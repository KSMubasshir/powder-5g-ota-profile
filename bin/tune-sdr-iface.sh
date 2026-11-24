#!/bin/bash
set -euo pipefail
BINDIR=$(dirname "$0")
source "$BINDIR/common.sh"
setup_begin "tune-sdr-iface"
sudo sysctl -w net.core.wmem_max=25000000
sudo sysctl -w net.core.rmem_max=25000000

SDR_IFACE=$(ip -o -4 addr show | awk '$4 ~ /^192\.168\.[0-9]+\.1\// {print $2; exit}')
if [[ -n $SDR_IFACE ]]; then
    sudo ip link set dev "$SDR_IFACE" mtu 9000
else
    echo "No Ethernet SDR interface found (normal for USB B210)."
fi
setup_complete
