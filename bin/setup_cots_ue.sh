#!/bin/bash
set -euo pipefail
BINDIR=`dirname $0`
source "$BINDIR/common.sh"
setup_begin "setup_cots_ue"

if [ $# -eq 0 ] || [ $# -gt 1 ]; then
    echo "usage: $0 [dnn]"
    exit 1
fi
DNN=$1
if [ ! -d "$MEREPODIR/.git" ]; then
    git clone https://gitlab.flux.utah.edu/dmaas/mobile-endpoints.git "$MEREPODIR"
    git -C "$MEREPODIR" checkout 6ebf537d9f256323c9fd2a179b558069faff9017
fi

echo "Configuring UE for DNN $DNN"

update_quectel_cm () {
    sudo sed -i "s/internet/$DNN/" /etc/systemd/system/quectel-cm.service
    sudo systemctl daemon-reload
    sudo systemctl restart quectel-cm.service
}

update_udhcpc_script () {
    sudo cp $MEBINDIR/default.script /etc/udhcpc/default.script
    sudo chmod +x /etc/udhcpc/default.script
}

update_quectel_cm
update_udhcpc_script
setup_complete
