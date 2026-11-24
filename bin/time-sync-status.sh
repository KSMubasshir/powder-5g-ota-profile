#!/bin/bash
# Observe host time and radio sensors without starting a transmit stream.
set -euo pipefail
source "$(dirname "$0")/setup-common.sh"
setup_begin time-sync-status refresh
if command -v ntpq >/dev/null 2>&1; then
    ntpq -pn || echo 'ntp peers unavailable'
    timedatectl || true
elif command -v chronyc >/dev/null 2>&1; then
    chronyc tracking || echo 'chrony tracking unavailable'
else
    timedatectl || echo 'host time status unavailable'
fi
case $(hostname -s) in
    gnb-*)
        if command -v uhd_usrp_probe >/dev/null 2>&1; then
            # Full output preserves ref_locked, clock/PPS and GPSDO sensor details
            # when the installed radio/driver provides them.
            timeout 30 uhd_usrp_probe || echo 'UHD sensors unavailable (radio may be busy)'
        else
            echo 'UHD probe unavailable'
        fi
        ;;
esac
setup_complete
