# Install Script for Visual Experience Data Base

### Command line scripts in order to install all the necessary dependencies for running the recording interface

### Please make sure your laptop is connected to the internet, open the terminal and follow the instructions

`sudo apt-get update && sudo apt-get upgrade`
`sudo dpkg --configure -a`

### Install and setup git
```javascript
sudo apt-get install git
ssh-keygen -t rsa

git config --global user.name "<your name>"\n
git config --global push.default matching\n
git config --global user.email "<your_email>"
```

### Master install from pupil recording interface repo
```javascript
mkdir ~/Code && cd ~/Code
git clone https://github.com/vedb/pupil_recording_interface.git
git checkout flir_recording
cd pupil_recording_interface/install_scripts/
```
### Master install from pomlab repo

### General softwares
`bash general_software.sh`

### Python modules
`bash python_modules.sh`

### Configure sync drives
`bash configure_sync_drives.sh`

### Install Pupil-labs 
`bash install_pupil.sh`

### Install Realsense dependencies
`bash install_realsense.sh`

### Install SPinnaker for running the FLIR Camera

### download the spinnaker file from [here](https://flir.app.boxcn.net/v/SpinnakerSDK/file/546280594576)
```javascript
cd ~/Downloads
tar xvzf spinnaker-1.27.0.48-Ubuntu18.04-amd64-pkg.tar.gz

sudo apt-get install libavcodec57 libavformat57 \
libswscale4 libswresample2 libavutil55 libusb-1.0-0 libgtkmm-2.4-dev
cd spinnaker-1.27.0.48-amd64
sudo sh install_spinnaker.sh
```
### During the installation follow these guidelines:
#### Answer Y to to this question:
##### Would you like to add a udev entry to allow access to USB hardware?
##### If this is not ran then your cameras may be only accessible by running #Spinnaker as sudo.
##### (Y/n)  Y

#### Press enter on this:
#### Adding new members to usergroup flirimaging...
#### Usergroup flirimaging is empty
#### To add a new member please enter username (or hit Enter to continue):

#### Answer Y to this question:
#### Writing the udev rules file...
#### Do you want to restart the udev daemon?
#### (Y/n)  Y

#### Then you should see this:
#### (ok) Restarting udev (via systemctl): udev.service.
#### Configuration complete.
#### A reboot may be required on some systems for changes to take effect.

#### Answer N to both of the last two questions:
#### Would you like to register the installed software?
#### (Y/n) N
#### Would you like to make a difference by participating in the Spinnaker feedback #program?
#### (Y/n) N


## USB Related configurations for linux (Important)

### On Linux systems, the USB-FS memory is restricted to 16 MB or less by default.
### To increase this limit follow these steps:

###    1. Open the /etc/default/grub file in any text editor. Find and replace:

###    GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"

###    with this:

###    GRUB_CMDLINE_LINUX_DEFAULT="quiet splash usbcore.usbfs_memory_mb=160000"

###    2. Update grub with these settings:
`$ sudo update-grub`

### 3. Reboot and test a USB 3.1 camera.


### Install PySpin for running the FLIR Camera

### download the PySpin file from [here](https://flir.app.boxcn.net/v/SpinnakerSDK/file/546281058590)

```javascript
cd ~/Downloads
tar xvzf spinnaker_python-1.27.0.48-Ubuntu18.04-cp36-cp36m-linux_x86_64.tar.gz
python3 -m pip install spinnaker_python-1.27.0.48-cp36-cp36m-linux_x86_64.whl
```