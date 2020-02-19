# Install Script for Visual Experience Data Base

### Command line scripts in order to install all the necessary dependencies for running the recording interface

### Please make sure your laptop is connected to the internet, open the terminal and follow the instructions

`sudo apt-get update && sudo apt-get upgrade`
`sudo dpkg --configure -a`

## Install and setup git

* `sudo apt-get install git`
* `ssh-keygen -t rsa`

* `git config --global user.name "<your name>"\n`
* `git config --global push.default matching\n`
* `git config --global user.email "<your_email>"\n`


## Master install from pupil recording interface repo

* `mkdir ~/Code && cd ~/Code`
* `git clone https://github.com/vedb/pupil_recording_interface.git`
* `git checkout flir_recording`
* `cd pupil_recording_interface/install_scripts/`

## Install different softwares and modules based on scripts

### General softwares
* `bash general_software.sh`

### Python modules
* `bash python_modules.sh`

### Configure sync drives
* `bash configure_sync_drives.sh`

### Install Pupil-labs 
* `bash install_pupil.sh`

### Install Realsense dependencies
* `bash install_realsense.sh`

### Now you can connect the T-265 to a USB port and run:

* `realsense-viewer`

### This will open up  the Intel Realsense Viewer user interface and you should see your tracking module on the top left cornenr, turn on the device, view 2D/3D visualizations, record, etc.
<img src="realsense-viewer.png">


## Install SPinnaker for running the FLIR Camera

### download the spinnaker files from [here](https://flir.app.boxcn.net/v/SpinnakerSDK/file/546280594576)

* `cd ~/Downloads # or any other directory that the compressed files are downloaded`
* `tar xvzf spinnaker-1.27.0.48-Ubuntu18.04-amd64-pkg.tar.gz`

* `sudo apt-get install libavcodec57 libavformat57 libswscale4 libswresample2 libavutil55 libusb-1.0-0 libgtkmm-2.4-dev`
* `cd spinnaker-1.27.0.48-amd64`
* `sudo sh install_spinnaker.sh`


### During the installation please follow these guidelines:
#### Answer Y to to this question:
##### Would you like to add a udev entry to allow access to USB hardware?
##### If this is not ran then your cameras may be only accessible by running Spinnaker as sudo.
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


## USB Related configurations for linux (<font color="red">Important</font>)

#### On Linux systems, the USB-FS memory is restricted to 16 MB or less by default.
#### To increase this limit follow these steps:

###    1. Open the /etc/default/grub file in any text editor. For example:
* `subl /etc/default/grub`

### Find and replace:

###    GRUB_CMDLINE_LINUX_DEFAULT=<font color="red">"quiet splash"</font>

###    with this:

###    GRUB_CMDLINE_LINUX_DEFAULT=<font color="red">""quiet splash usbcore.usbfs_memory_mb=160000""</font>

###    2. Update grub with these settings:
* `sudo update-grub`

### 3. Restart your system

### To confirm that the memory limit has been successfully updated, run the following command:

* `cat /sys/module/usbcore/parameters/usbfs_memory_mb`
### It should return the new value that you set above

### Now you can connect a FLIR Camera to a USB 3.1 port and run:

* `spinview`

### This will open up  the spinview user interface and you can select the camera, record image/video, etc.
<img src="screenshot_spinview.png">

## Install PySpin for running the FLIR Camera
### In order to communicate with the FLIR camera we use the PySpin python wrapper
### download the PySpin file from [here](https://flir.app.boxcn.net/v/SpinnakerSDK/file/546281058590)

* `cd ~/Downloads # or any other directory that the compressed files are downloaded`
* `ar xvzf spinnaker_python-1.27.0.48-Ubuntu18.04-cp36-cp36m-linux_x86_64.tar.gz`
* `python3 -m pip install spinnaker_python-1.27.0.48-cp36-cp36m-linux_x86_64.whl`


## Next
### That's it! You're done installing all the necessary softwares and modules!
### You can call the record_video_flir.py to record 30 seconds of data streamed from different devices

* `cd ~/Code/pupil_recording_interface/examples/`
* `python3 record_video_flir.py`
