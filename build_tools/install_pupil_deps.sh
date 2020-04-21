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

### Set workspace
export PUPIL_WS="$(dirname "$(realpath "$0")")/../build"
mkdir -p "${PUPIL_WS}"

### Install dependencies
sudo apt-get install -y \
  pkg-config cmake build-essential nasm wget libusb-1.0-0-dev

# ffmpeg
sudo apt-get install -y \
  libavformat-dev libavcodec-dev libavdevice-dev \
  libavutil-dev libswscale-dev libavresample-dev ffmpeg x264 x265 \
  libportaudio2 portaudio19-dev

# OpenCV
sudo apt-get install -y python3-opencv libopencv-dev

# 3D Eye model dependencies
sudo apt-get install -y \
  libgoogle-glog-dev libatlas-base-dev libeigen3-dev libceres-dev

# turbojpeg
cd "${PUPIL_WS}"
wget -O libjpeg-turbo.tar.gz https://sourceforge.net/projects/libjpeg-turbo/files/1.5.1/libjpeg-turbo-1.5.1.tar.gz/download
tar xvzf libjpeg-turbo.tar.gz
cd libjpeg-turbo-1.5.1
./configure --enable-static=no --prefix=/usr/local
sudo make install
sudo ldconfig

# uvc
cd "${PUPIL_WS}"
git clone https://github.com/pupil-labs/libuvc
cd libuvc
mkdir build
cd build
cmake ..
make && sudo make install

echo 'SUBSYSTEM=="usb",  ENV{DEVTYPE}=="usb_device", GROUP="plugdev", MODE="0664"' | sudo tee /etc/udev/rules.d/10-libuvc.rules > /dev/null
sudo udevadm trigger

### Success!
echo "Installation successful!"
cd "${cwd}"
