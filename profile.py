#!/usr/bin/env python

"""Generate the outdoor 5G allocation and its ordered startup services."""
import os
import re

import geni.portal as portal
import geni.rspec.pg as pg
import geni.rspec.igext as ig
import geni.rspec.emulab.pnext as PN
import geni.rspec.emulab.spectrum as spectrum
import geni.rspec.emulab.route as route


tourDescription = """
### Outdoor 5G measurement network
Allocates an Open5GS core, dense-site B210 gNodeBs and fixed COTS UE endpoints.
Defaults select Mario, Guest House and USTAR, plus EBC, Moran and Guest House
fixed endpoints, and request 3430-3450 MHz. The gNodeBs do not start at boot.
An approved spectrum and hardware reservation is required before transmission.
"""
tourInstructions = """
Wait for every Startup entry to show Finished. Inspect /local/logs/ and
/local/setup/ on each node. Run /local/repository/bin/time-sync-status.sh;
on fixed endpoints also run sudo /local/repository/bin/ue-status.sh.
The core starts automatically. Start gNodeBs only during the approved reservation,
using the experiment controller or sudo systemctl start srs-gnb.service.
Stop with sudo systemctl stop srs-gnb.service before the reservation ends.
Adjacent dense sites Moran/USTAR and Guesthouse/EBC can interfere.
Optional Grafana on orch uses the per-experiment password in the manifest.
See README.md for parameters, verification and collection commands.
"""

class GLOBALS:
    BIN_PATH = "/local/repository/bin"
    ETC_PATH = "/local/repository/etc"
    UBUNTU_IMG = "urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU22-64-STD"
    COTS_UE_IMG = "urn:publicid:IDN+emulab.net+image+PowderTeam:cots-jammy-image"
    COMP_MANAGER_ID = "urn:publicid:IDN+emulab.net+authority+cm"
    DEFAULT_SRSRAN_HASH = "5e6f50a202c6efa671d5b231d7c911dc6c3d86ed"
    SRSRAN_DEPLOY_SCRIPT = os.path.join(BIN_PATH, "deploy-srsran.sh")
    OPEN5GS_DEPLOY_SCRIPT = os.path.join(BIN_PATH, "deploy-open5gs.sh")
    MEASUREMENT_SCRIPT = BIN_PATH + "/deploy-measurement-tools.sh"
    TEST_TOOLS_DEPLOY_SCRIPT = os.path.join(BIN_PATH, "deploy-test-tools.sh")


def gnb_cn_pair(idx, dense_radio):
    node = request.RawPC("gnb-{}".format(dense_radio.device.split("-")[-1]))
    node.component_manager_id = GLOBALS.COMP_MANAGER_ID
    node.component_id = dense_radio.device
    node.disk_image = GLOBALS.UBUNTU_IMG
    nodeb_cn_if = node.addInterface("nodeb-cn-if")
    nodeb_cn_if.addAddress(pg.IPv4Address("192.168.1.{}".format(idx + 2), "255.255.255.0"))
    cn_link.addInterface(nodeb_cn_if)

    if params.deploy_srsran:
        if params.include_orch:
            cmd = "{} {}".format(GLOBALS.TEST_TOOLS_DEPLOY_SCRIPT, "nodeb")
            node.addService(pg.Execute(shell="bash", command=cmd))

        cmd = "{} '{}'".format(GLOBALS.SRSRAN_DEPLOY_SCRIPT, params.srsran_commit)
        node.addService(pg.Execute(shell="bash", command=cmd))
        if params.start_gnbs:
            node.addService(pg.Execute(shell="bash", command="sudo systemctl restart srs-gnb.service"))

    node.addService(pg.Execute(shell="bash", command=GLOBALS.MEASUREMENT_SCRIPT))

    if params.start_vnc_dense:
        node.startVNC()

def fixed_node(_, f_node_tuple):
    node = request.RawPC("{}-{}".format(f_node_tuple.fe_id, "nuc1"))
    agg_full_name = "urn:publicid:IDN+{}.powderwireless.net+authority+cm".format(f_node_tuple.fe_id)
    node.component_manager_id = agg_full_name
    node.component_id = "nuc1"
    node.disk_image = GLOBALS.COTS_UE_IMG
    node.addService(pg.Execute(shell="bash", command=GLOBALS.MEASUREMENT_SCRIPT))
    if params.start_vnc_fixed:
        node.startVNC()

pc = portal.Context()

node_types = [
    ("d430", "Emulab, d430"),
    ("d740", "Emulab, d740"),
    ("d760p", "Emulab, d760"),
    ("d760-gpu", "Emulab, d760 w/ GPU"),
]

pc.defineParameter(
    name="include_orch",
    description="Include orchestrator node for centralized logging (Grafana/Loki). Install logging" \
                "tools (Promtail) on all nodes.",
    typ=portal.ParameterType.BOOLEAN,
    defaultValue=False,
    longDescription="Allocate Grafana/Loki and install log forwarders when enabled."
)

pc.defineParameter(
    name="include_mobiles",
    description="Include mobile endpoints in the experiment. (Only enable if this experiment is" \
                "meant to last until the end of the day. Otherwise, instantiate a separate" \
                "experiment using the mobile endpoints profile.)",
    typ=portal.ParameterType.BOOLEAN,
    defaultValue=False
)

pc.defineParameter(
    name="dnn",
    description="DNN/APN for COTS UEs to connect to (if mobile endpoints are included).",
    typ=portal.ParameterType.STRING,
    defaultValue="internet",
    longDescription="DNN/APN that the connection manager will select for the UE."
)

pc.defineParameter(
    name="orch_nodetype",
    description="Type of compute node to use for Orch node (if included)",
    typ=portal.ParameterType.STRING,
    defaultValue=node_types[0],
    legalValues=node_types
)

pc.defineParameter(
    name="cn_nodetype",
    description="Type of compute node to use for CN node",
    typ=portal.ParameterType.STRING,
    defaultValue=node_types[0],
    legalValues=node_types
)

dense_radios = [
    ("cnode-mario", "Mario"),
    ("cnode-moran", "Moran"),
    ("cnode-guesthouse", "Guesthouse"),
    ("cnode-ebc", "EBC"),
    ("cnode-ustar", "USTAR"),
]

pc.defineStructParameter(
    "dense_radios", "Dense Site Radios",
    [{"device": "cnode-mario"}, {"device": "cnode-guesthouse"}, {"device": "cnode-ustar"}],
    multiValue=True,
    min=1,
    multiValueTitle="Dense Site NUC+B210 radios to allocate.",
    members=[
        portal.Parameter(
            "device",
            "SFF Compute + NI B210 device",
            portal.ParameterType.STRING,
            dense_radios[0], dense_radios,
            longDescription="A Small Form Factor compute with attached NI B210 device at the given" \
                            "Dense Deployment site will be allocated."
        ),
    ]
)

portal.context.defineStructParameter(
    "freq_ranges", "Frequency Ranges To Transmit In",
    defaultValue=[{"freq_min": 3430.0, "freq_max": 3450.0}],
    multiValue=True,
    min=0,
    multiValueTitle="Frequency ranges to be used for transmission.",
    members=[
        portal.Parameter(
            "freq_min",
            "Frequency Range Min",
            portal.ParameterType.BANDWIDTH,
            3430.0,
            longDescription="Values are rounded to the nearest kilohertz."
        ),
        portal.Parameter(
            "freq_max",
            "Frequency Range Max",
            portal.ParameterType.BANDWIDTH,
            3450.0,
            longDescription="Values are rounded to the nearest kilohertz."
        ),
    ]
)

pc.defineParameter(
    name="start_gnbs",
    description="Automatically start the srsRAN gNodeBs",
    typ=portal.ParameterType.BOOLEAN,
    defaultValue=False,
    advanced=True
)

pc.defineParameter(
    name="os_image",
    description="Mobile endpoints disk image",
    typ=portal.ParameterType.STRING,
    defaultValue=GLOBALS.COTS_UE_IMG,
    longDescription="File system image for the node.",
    advanced=True
)

pc.defineParameter(
    name="deploy_srsran",
    description="Deploy srsRAN",
    typ=portal.ParameterType.BOOLEAN,
    defaultValue=True,
    advanced=True
)

pc.defineParameter(
    name="start_vnc_dense",
    description="enable noVNC on dense nodes",
    typ=portal.ParameterType.BOOLEAN,
    defaultValue=True,
    advanced=True
)

pc.defineParameter(
    name="start_vnc_mobile",
    description="enable noVNC on mobile endpoints",
    typ=portal.ParameterType.BOOLEAN,
    defaultValue=True,
    advanced=True
)

pc.defineParameter(
    name="start_vnc_fixed",
    description="enable noVNC on fixed endpoint nodes",
    typ=portal.ParameterType.BOOLEAN,
    defaultValue=True,
    advanced=True
)

fixed_radios = [
    ("web", "WEB, nuc1"),
    ("bookstore", "Bookstore, nuc1"),
    ("humanities", "Humanities, nuc1"),
    ("law73", "Law 73, nuc1"),
    ("ebc", "EBC, nuc1"),
    ("madsen", "Madsen, nuc1"),
    ("sagepoint", "Sage Point, nuc1"),
    ("moran", "Moran, nuc1"),
    ("cpg", "Central Parking Garage, nuc1"),
    ("guesthouse", "Guest House, nuc1"),
]

pc.defineStructParameter(
    "fixed_radios", "Fixed Endpoint Radios",
    [{"fe_id": "ebc"}, {"fe_id": "moran"}, {"fe_id": "guesthouse"}],
    multiValue=True,
    min=0,
    multiValueTitle="Fixed endpoint NUC+B210/COTSUE radios to allocate.",
    members=[
        portal.Parameter(
            "fe_id",
            "SFF Compute + NI B210 device + COTS UE",
            portal.ParameterType.STRING,
            fixed_radios[0], fixed_radios,
            longDescription="A small form factor compute with attached NI B210 and COTS UE the" \
                            "given Fixed Endpoint site will be allocated."
        ),
    ],
    advanced=True
)

pc.defineParameter(
    "srsran_commit", "srsRAN Project commit", portal.ParameterType.STRING,
    GLOBALS.DEFAULT_SRSRAN_HASH, advanced=True,
    longDescription="The deployment and its logging were checked against the pinned commit; another commit needs the same checks, and the supplied patch must apply to it."
)

params = pc.bindParameters()
# Retain upstream verification and warn about known adjacent dense sites.
selected = {item.device for item in params.dense_radios}
for left, right in [("cnode-moran", "cnode-ustar"), ("cnode-guesthouse", "cnode-ebc")]:
    if left in selected and right in selected:
        pc.reportWarning(portal.ParameterWarning(
            "Adjacent dense sites {} and {} can interfere.".format(left, right), ["dense_radios"]))
if not re.match(r"[0-9a-fA-F]{40}\Z", params.srsran_commit):
    pc.reportError(portal.ParameterError("Use a full 40-character commit hash.", ["srsran_commit"]))
if not re.match(r"[A-Za-z0-9_.-]+\Z", params.dnn):
    pc.reportError(portal.ParameterError("Use an APN consisting of letters, digits, dots, hyphens or underscores.", ["dnn"]))
pc.verifyParameters()
request = pc.makeRequestRSpec()

cn_node = request.RawPC("cn5g")
cn_node.component_manager_id = GLOBALS.COMP_MANAGER_ID
cn_node.hardware_type = params.cn_nodetype
cn_node.disk_image = GLOBALS.UBUNTU_IMG
cn_if = cn_node.addInterface("cn-if")
cn_if.addAddress(pg.IPv4Address("192.168.1.1", "255.255.255.0"))
cn_link = request.Link("cn-link")
cn_link.setNoBandwidthShaping()
cn_link.addInterface(cn_if)

if params.include_orch:
    cmd = "{} {}".format(GLOBALS.TEST_TOOLS_DEPLOY_SCRIPT, "core")
    cn_node.addService(pg.Execute(shell="bash", command=cmd))

cn_node.addService(pg.Execute(shell="bash", command=GLOBALS.OPEN5GS_DEPLOY_SCRIPT))
cn_node.addService(pg.Execute(shell="bash", command=GLOBALS.MEASUREMENT_SCRIPT))

for idx, dense_radio in enumerate(params.dense_radios):
    gnb_cn_pair(idx, dense_radio)

for idx, fixed_radio in enumerate(params.fixed_radios):
    fixed_node(idx, fixed_radio)

for frange in params.freq_ranges:
    request.requestSpectrum(frange.freq_min, frange.freq_max, 0)

if params.include_orch:
    orch = request.RawPC("orch")
    orch.component_manager_id = GLOBALS.COMP_MANAGER_ID
    orch.hardware_type = params.orch_nodetype
    orch.disk_image = GLOBALS.UBUNTU_IMG
    orch_if = orch.addInterface("orch-if")
    orch_if.addAddress(
        pg.IPv4Address("192.168.1.{}".format(len(params.dense_radios) + 2),
                          "255.255.255.0")
    )
    cn_link.addInterface(orch_if)
    cmd = "{} {}".format(GLOBALS.TEST_TOOLS_DEPLOY_SCRIPT, "orch")
    orch.addService(pg.Execute(shell="bash", command=cmd))
    orch.addService(pg.Execute(shell="bash", command=GLOBALS.MEASUREMENT_SCRIPT))


if params.include_mobiles:
    all_routes = request.requestAllRoutes()
    all_routes.disk_image = params.os_image
    if params.include_orch:
        all_routes.addService(
            pg.Execute(shell="bash", command="sudo /local/repository/bin/deploy_mobile_tools.sh orch")
        )
    all_routes.addService(
        pg.Execute(shell="bash", command="sudo /local/repository/bin/setup_cots_ue.sh {}".format(params.dnn))
    )

    all_routes.addService(pg.Execute(shell="bash", command=GLOBALS.MEASUREMENT_SCRIPT))

    if params.start_vnc_mobile:
        all_routes.startVNC()

tour = ig.Tour()
tour.Description(ig.Tour.MARKDOWN, tourDescription)
tour.Instructions(ig.Tour.MARKDOWN, tourInstructions)
request.addTour(tour)

# Password for grafana.
request.addResource(ig.Password("perExptPassword"))

pc.printRequestRSpec(request)
