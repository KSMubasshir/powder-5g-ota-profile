#!/bin/bash
set -euo pipefail
COMMIT_HASH=${1:?usage: deploy-srsran.sh COMMIT_HASH}
BINDIR=`dirname $0`
ETCDIR=/local/repository/etc
source "$BINDIR/common.sh"
setup_begin "deploy-srsran"


# Get the emulab repo
while ! wget -qO - http://repos.emulab.net/emulab.key | sudo apt-key add -
do
    echo Failed to get emulab key, retrying
done

while ! sudo add-apt-repository -y http://repos.emulab.net/powder/ubuntu/
do
    echo Failed to add POWDER package repository, retrying
done

while ! sudo env DEBIAN_FRONTEND=noninteractive apt-get update
do
    echo Failed to update, retrying
done

sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y libuhd-dev uhd-host
sudo uhd_images_downloader -tb2

sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
  cmake \
  make \
  gcc \
  g++ \
  pkg-config \
  libfftw3-dev \
  libmbedtls-dev \
  libsctp-dev \
  libyaml-cpp-dev \
  libgtest-dev

cd $SRCDIR
if [ ! -d srsRAN_Project/.git ]; then
    git clone "$SRS_PROJECT_REPO"
fi
cd srsRAN_Project
git checkout "$COMMIT_HASH"
if ! git apply --reverse --check "$ETCDIR/srsran/srsran.patch" 2>/dev/null; then
    git apply "$ETCDIR/srsran/srsran.patch"
fi
mkdir -p build
cd build
cmake ../
make -j $(nproc)

echo configuring nodeb...
mkdir -p $SRCDIR/etc/srsran
cp -r $ETCDIR/srsran/* $SRCDIR/etc/srsran/
LANIF=`ip r | awk '/192\.168\.1\.0/{print $3}'`
if [ ! -z $LANIF ]; then
  LANIP=`ip r | awk '/192\.168\.1\.0/{print $NF}'`
  echo LAN IFACE is $LANIF IP is $LANIP.. updating nodeb config
  find $SRCDIR/etc/srsran/ -type f -exec sed -i "s/LANIP/$LANIP/" {} \;
  IPLAST=`echo $LANIP | awk -F. '{print $NF}'`
  find $SRCDIR/etc/srsran/ -type f -exec sed -i "s/GNBID/$IPLAST/" {} \;
else
  echo No LAN IFACE.. not updating nodeb config
fi
echo configuring nodeb... done.
sudo cp "$SERVICESDIR/srs-gnb.service" /etc/systemd/system/
sudo systemctl daemon-reload
setup_complete
