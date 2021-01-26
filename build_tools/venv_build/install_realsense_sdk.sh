#!/bin/bash

set -e

### Save working directory
cwd=$(pwd)
function cleanup {
  echo "Installation failed"
  cd "${cwd}"
  exec $SHELL
}
trap cleanup ERR

export UBUNTU_VERSION=$(lsb_release -sc)

### install SDK
sudo apt-key adv --keyserver keys.gnupg.net --recv-key C8B3A55A6F3EFCDE || \
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-key C8B3A55A6F3EFCDE

sudo add-apt-repository \
"deb http://realsense-hw-public.s3.amazonaws.com/Debian/apt-repo ${UBUNTU_VERSION} main" -u

sudo apt-get update

sudo apt-get install -y \
 librealsense2-dkms librealsense2-utils librealsense2-dev \
 librealsense2-udev-rules
