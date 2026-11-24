#!/bin/bash
# Archive available setup, gNodeB and core logs into a new destination file.
set -euo pipefail
source "$(dirname "$0")/setup-common.sh"
setup_begin collect-logs refresh
if [[ $# -ne 1 ]]; then
    echo "usage: $0 DEST.tar.gz" >&2
    exit 2
fi
dest=$1
umask 077
# Noclobber also refuses symlinks and prevents replacing a prior archive.
set -C
exec 3> "$dest"
paths=(local/logs)
for path in var/log/srs-gnb.log var/log/open5gs; do
    [[ ! -e /$path ]] || paths+=("$path")
done
if ! sudo tar -C / -czf - "${paths[@]}" >&3; then
    exec 3>&-
    echo "Archive failed; incomplete output retained at $dest" >&2
    exit 1
fi
exec 3>&-
setup_complete
