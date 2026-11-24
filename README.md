# Outdoor 5G measurement profile

A repository-based POWDER profile with srsRAN Project gNodeBs, an Open5GS core,
fixed COTS UE endpoints, and optional Grafana/Loki and mobile endpoints.
The deployment scripts and configuration originate from POWDER's
`srs-outdoor-ota` profile, snapshot `55563fa`.

The default allocation is:

| Node | Resource | Experiment LAN |
| --- | --- | --- |
| `gnb-mario` | `cnode-mario`, NUC + B210 | `192.168.1.2/24` |
| `gnb-guesthouse` | `cnode-guesthouse`, NUC + B210 | `192.168.1.3/24` |
| `gnb-ustar` | `cnode-ustar`, NUC + B210 | `192.168.1.4/24` |
| `cn5g` | d430, Open5GS | `192.168.1.1/24` |
| `ebc-nuc1` | EBC fixed endpoint, COTS UE image | management network |
| `moran-nuc1` | Moran fixed endpoint, COTS UE image | management network |
| `guesthouse-nuc1` | Guest House fixed endpoint, COTS UE image | management network |

The request includes 3430–3450 MHz. Dense/core/orchestrator nodes use
`urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU22-64-STD`;
fixed endpoints use
`urn:publicid:IDN+emulab.net+image+PowderTeam:cots-jammy-image`.
No gNodeB starts at boot by default. The core starts during setup.
Hardware and spectrum must be reserved and approved before radio operation.
Node clocks and radio reference locks are separate checks; neither proves calibrated
propagation delay or aligned radio frames. Successful allocation does not guarantee links.

## Parameters

| Portal parameter | Default | Effect |
| --- | --- | --- |
| `dense_radios[].device` | `cnode-mario`, `cnode-guesthouse`, `cnode-ustar`, in order | Allocates one gNodeB per site; LAN addresses start at `.2` in selection order. Full choices: Mario, Moran, Guesthouse, EBC, USTAR. |
| `fixed_radios[].fe_id` | `ebc`, `moran`, `guesthouse` | Allocates `nuc1` at each site; also offers WEB, Bookstore, Humanities, Law 73, Madsen, Sage Point and Central Parking Garage. Empty list is allowed. |
| `freq_ranges[].freq_min`, `.freq_max` | `3430`, `3450` MHz | Spectrum requests, with upstream zero-power argument. Values round to kHz. Changing a request does not retune the supplied radio configuration. |
| `start_gnbs` | `false` | Advanced: explicitly opt into starting the installed gNodeB service at startup. |
| `deploy_srsran` | `true` | Advanced: deploy the pinned stack, patch, configs and service. Disabling this leaves those to the operator. |
| `srsran_commit` | `5e6f50a202c6efa671d5b231d7c911dc6c3d86ed` | Advanced: full commit hash. The deployment and its logging were checked against this commit; another commit needs the same checks, and the patch must apply to it. |
| `include_orch` | `false` | Adds `orch`, Grafana/Loki and log forwarders on core/gNodeBs and included mobiles. Orchestrator LAN address follows the last dense site. |
| `include_mobiles` | `false` | Includes all routes using the upstream route request. Requires appropriate mobile reservations; use a separate mobile experiment for shorter sessions. |
| `cn_nodetype` | `d430` | Core hardware. Choices: `d430`, `d740`, `d760p`, `d760-gpu`. |
| `orch_nodetype` | `d430` | Same choices, used only when `include_orch` is enabled. |
| `os_image` | COTS UE image above | Advanced: image for included mobile routes only; fixed endpoint image is unchanged. |
| `dnn` | `internet` | DNN/APN for included mobile connection managers; the Open5GS test subscribers retain `internet`. |
| `start_vnc_dense` | `true` | Advanced: enable noVNC on dense nodes. |
| `start_vnc_mobile` | `true` | Advanced: enable noVNC on included mobile routes. |
| `start_vnc_fixed` | `true` | Advanced: enable noVNC on fixed endpoints. |

Selecting Moran/USTAR or Guesthouse/EBC dense pairs registers a parameter warning
about adjacent-site interference. Review the selection before proceeding.

## Instantiation

Push this repository to an empty public GitHub repository after review. In the
POWDER portal choose **Create Profile → Git Repository**, supply its repository
URL, use branch `master`, and choose `profile.py` as the profile script. Create the
profile, then select **Instantiate**.

Keep all parameter defaults for the allocation above: three dense rows in the
listed order, three fixed rows, 3430–3450 MHz, deployment enabled, automatic
gNodeB start disabled, orchestrator and mobiles disabled. Select your approved
project, experiment name and reservation/start/end time in the portal. Verify that
the reserved dense sites, fixed endpoints, core compute and spectrum match the
request. This repository does not make reservations.

## After startup

Wait for every node's Startup column to show **Finished**. Setup output is in
`/local/logs/<script>.log`; success markers are `/local/setup/<script>.complete`.
A failed setup must not have a completion marker. Installers skip a completed
setup; remove only the relevant marker if intentionally reconfiguring a node.
Status and collection scripts run afresh on each invocation and update their
marker only after success. The shared `common.sh` and `setup-common.sh` are sourced
libraries, not startup entry points.

On every node, check `/var/tmp/meas` is writable by the experiment user and run:

```bash
/local/repository/bin/time-sync-status.sh
```

On gNodeBs verify the pinned source and binary, then confirm the service is inactive:

```bash
git -C /var/tmp/srsRAN_Project rev-parse HEAD
test -x /var/tmp/srsRAN_Project/build/apps/gnb/gnb
systemctl is-active srs-gnb.service
```

`inactive` (exit 3) is expected before a controller starts the cell. The service
is installed independently of Grafana/Loki. The supplied radio configuration stays
upstream-identical, including its internal timing defaults; a measurement controller
must supply its own validated configuration, external clock/PPS settings and log paths.
`uhd_usrp_probe` reports available clock/reference/GPSDO sensors without transmitting;
busy or absent hardware is reported as unavailable, never as a locked reference.

On `cn5g`, inspect `systemctl status open5gs-amfd.service` and
`/var/log/open5gs/`. Core configuration and the upstream public test-SIM provisioning
range (test PLMN `99999`, subscriber suffixes `100` through `150`) are unchanged.
The fixed COTS UE image retains its existing modem/connection-manager setup.
On a fixed endpoint:

```bash
sudo /local/repository/bin/ue-status.sh
# If automatic discovery cannot identify exactly one modem AT interface:
sudo /local/repository/bin/ue-status.sh /dev/ttyUSB2
```

This prints modem identity, subscriber identity, serving-cell/network state and
`quectel-cm` service status. Protect the resulting logs. It sends only `ATI`,
`AT+CIMI`, `AT+QENG="servingcell"` and `AT+QNWINFO`. Confirm the dedicated AT interface
before use, and avoid another AT reader on the same port.

Start cells with the experiment controller only within the approved window; manual
operation uses `sudo systemctl start srs-gnb.service` and
`sudo systemctl stop srs-gnb.service`. For cleanup, stop every cell before the window
ends. To archive logs to a new file in the experiment user's measurement directory:

```bash
/local/repository/bin/collect-logs.sh /var/tmp/meas/startup.tar.gz
```

The archive contains `/local/logs`, plus `/var/log/srs-gnb.log` and
`/var/log/open5gs` where present. It refuses an existing destination; changing live
logs can cause tar to report failure, retaining the incomplete archive for inspection.
Controller-specific data outside these paths must be collected separately.
When enabled, Grafana is on `http://orch:3000/`, with its per-experiment password
from the portal manifest. Do not publish manifests, archives or private setup state.

## Differences from srs-outdoor-ota

All `etc/open5gs/*`, `etc/srsran/*` (including the TDD patch), `etc/grafana/*` and
`services/srs-gnb.service` are copied byte for byte. No upstream file is dropped.
The stack commit, build location, images, subscriber provisioning, resource choices,
node names and base deployment remain the same. Changes are:

| File | Change and reason |
| --- | --- |
| `profile.py` | Python 3 entry point (mobile routes use the upstream `requestAllRoutes()` call unchanged), `GLOBALS`, concise tour, explicit topology defaults, orchestrator default false, advanced pinned commit parameter and format validation, safe APN validation, adjacent-site warnings, and measurement setup after each node's main deployment (including optional routes/orchestrator). Upstream `verifyParameters()` is retained. |
| `bin/common.sh` | Sources the new shared setup helpers; upstream directory and repository definitions remain unchanged. |
| `bin/setup-common.sh` | New shared log/marker functions; noninteractive package environment; markers are success-only. |
| `bin/deploy-srsran.sh` | Shared logs/markers, strict error handling, quoted hash, retry-safe clone/build/patch, and unconditional service installation after build so the default deployment can run without the orchestrator. Removes an upstream personal-name comment. |
| `bin/deploy-open5gs.sh` | Shared logs/markers and strict errors, duplicate-safe NAT rule reapplied on later boots, noninteractive package operations, replace-safe keyring/logrotate generation. Public test-SIM provisioning and all Open5GS configurations remain unchanged. |
| `bin/deploy-test-tools.sh` | Shared logs/markers, strict errors, correct self-script path and role on user re-execution, private temporary runtime credential directory removed on exit, no shell tracing of generated secrets, and retry-safe Loki directory creation. Grafana/Loki/Promtail versions and roles remain upstream. |
| `bin/deploy_mobile_tools.sh` | Shared logs/markers, strict errors and retry-safe clone; retains the upstream mobile dependency pin and public source URL. |
| `bin/setup_cots_ue.sh` | Shared logs/markers and strict errors; fetches the same pinned mobile dependency if absent so included mobiles also work without the orchestrator. |
| `bin/tune-cpu.sh` | Shared logs/markers and strict errors; upstream tuning commands retained. Available for explicit operator use, not added to startup. |
| `bin/tune-sdr-iface.sh` | Shared logs/markers and strict errors; modern interface lookup and harmless skip on USB B210 nodes. Available for explicit operator use, not added to startup. |
| `bin/deploy-measurement-tools.sh` | Installs tcpdump, tshark with setuid disabled, python3-yaml, jq, rsync and tmux (not chrony: the testbed's own NTP daemon stays in place); creates user-owned `/var/tmp/meas`. |
| `bin/time-sync-status.sh`, `bin/ue-status.sh`, `bin/collect-logs.sh` | New observation and collection commands described above. |
| `README.md`, `.gitignore` | New operator documentation and local artifact exclusions. |

No real SIM secrets, credentials or generated passwords belong in this repository.
Only the original public laboratory test-SIM constants are preserved for deployment
parity. Validate real hardware, radio locks, link quality and measurements in a
separate reserved experiment; offline RSpec and shell validation cannot establish them.
