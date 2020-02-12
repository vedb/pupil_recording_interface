# All installation scripts go here


# Install Spinnaker (spinview and all FLIR related softwares)
sudo apt-get install libavcodec57 libavformat57 \
libswscale4 libswresample2 libavutil55 libusb-1.0-0 libgtkmm-2.4-dev

sudo sh install_spinnaker.sh


#sudo apt-get install python-pip python3-pip
#install the PySpin
python3 -m pip install --user spinnaker_python-1.27.0.48-cp36-cp36m-linux_x86_64.whl

