#!/bin/bash
# Install capture and observation tools; do not start radio services.
set -euo pipefail
source "$(dirname "$0")/setup-common.sh"
# Completion state: /local/setup; setup output: /local/logs.
setup_begin deploy-measurement-tools
export DEBIAN_FRONTEND=noninteractive
echo 'wireshark-common wireshark-common/install-setuid boolean false' | sudo debconf-set-selections
sudo env DEBIAN_FRONTEND=noninteractive apt-get update
# No chrony: installing it would replace the testbed-managed NTP daemon and its local servers.
packages=(tcpdump tshark python3-yaml jq rsync tmux)
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}"
experiment_user=$(geni-get user_urn 2>/dev/null | awk -F+ '{print $NF}' || true)
[[ -n $experiment_user ]] || experiment_user=$(id -un)
id "$experiment_user" >/dev/null
sudo install -d -m 0755 -o "$experiment_user" -g "$(id -gn "$experiment_user")" /var/tmp/meas
setup_complete
