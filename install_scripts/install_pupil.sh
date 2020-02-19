# Installs pupils-lab python packages

###############################################################################
# Install general dependencies

sudo apt install -y pkg-config git cmake build-essential nasm wget python3-setuptools libusb-1.0-0-dev  python3-dev python3-pip python3-numpy python3-scipy libglew-dev libglfw3-dev libtbb-dev

# ffmpeg >= 3.2
sudo apt install -y libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libswscale-dev libavresample-dev ffmpeg x264 x265 libportaudio2 portaudio19-dev

# OpenCV >= 3
sudo apt install -y python3-opencv libopencv-dev

# 3D Eye model dependencies
sudo apt install -y libgoogle-glog-dev libatlas-base-dev libeigen3-dev
sudo apt install -y libceres-dev

###############################################################################
# Install Turbojpeg

cd ~/Code
mkdir Turbojpeg
cd Turbojpeg
wget -O libjpeg-turbo.tar.gz https://sourceforge.net/projects/libjpeg-turbo/files/1.5.1/libjpeg-turbo-1.5.1.tar.gz/download
tar xvzf libjpeg-turbo.tar.gz
cd libjpeg-turbo-1.5.1
./configure --enable-static=no --prefix=/usr/local
sudo make install
sudo ldconfig

###############################################################################
# Install libuvc

cd ~/Code
git clone https://github.com/pupil-labs/libuvc
cd libuvc
mkdir build
cd build
cmake ..
make && sudo make install

###############################################################################
# Adding the following udev rules to run libuvc as normal user
cd ~/Code
echo 'SUBSYSTEM=="usb",  ENV{DEVTYPE}=="usb_device", GROUP="plugdev", MODE="0664"' | sudo tee /etc/udev/rules.d/10-libuvc.rules > /dev/null
sudo udevadm trigger

###############################################################################
# Install libuvc
python3 -m pip install --upgrade pip

pip3 install cysignals
pip3 install cython
pip3 install msgpack==0.5.6
pip3 install numexpr
pip3 install packaging
pip3 install psutil
pip3 install pyaudio
pip3 install pyopengl
pip3 install pyzmq
pip3 install scipy
pip3 install git+https://github.com/zeromq/pyre

pip3 install pupil-apriltags
pip3 install pupil-detectors
pip3 install git+https://github.com/pupil-labs/PyAV
pip3 install git+https://github.com/pupil-labs/pyuvc
pip3 install git+https://github.com/pupil-labs/pyndsi
pip3 install git+https://github.com/pupil-labs/pyglui
pip3 install git+https://github.com/pupil-labs/nslr
pip3 install git+https://github.com/pupil-labs/nslr-hmm

# I found this useful to prevent the following uvc error
#    from uvc import get_time_monotonic
#ImportError: libuvc.so.0: cannot open shared object file: No such file or directory

sudo ldconfig

###############################################################################
# Clone pupils-lab repo in order to run from source

cd ~/Code
git clone https://github.com/pupil-labs/pupil.git # or your fork
cd pupil
cd pupil_src
#python3 main.py capture # or player/service





