# Software installation via PPAs

### General

# Vim (mo betta than vi)
sudo apt-get --assume-yes install vim
# TODO: Vim colors (monokai)
# TODO: git gutter for vim: https://github.com/airblade/vim-gitgutter

# Utilities
sudo apt-get --assume-yes install htop
sudo apt-get --assume-yes install tree
sudo apt-get --assume-yes install ncdu

# Screen sharing
sudo apt-get --assume-yes install byobu


# Okular, pdf and image viewer (better than default)
sudo apt-get --assume-yes install okular


# Nextcloud client
# NOPE NOPE NOPE: Nextcloud client version 2.5 is awful.
#sudo add-apt-repository ppa:nextcloud-devs/client
#sudo apt-get update
#sudo apt-get --assume-yes install nextcloud-client
# This is equivalent to the much less buggy Nextcloud Client version 2.4
sudo apt-get install owncloud-client

# Password management for owncloud
sudo apt-get install libgnome-keyring0


### Libraries

# OpenBLAS parallelization over multiple cores
sudo apt-get --assume-yes install libopenblas-dev 

# OpenGL
sudo apt-get --assume-yes install libglw1-mesa libglw1-mesa-dev
sudo apt-get --assume-yes install freeglut3-dev


# Sublime, the badass text editor (from https://launchpad.net/~webupd8team/+archive/ubuntu/sublime-text-3)
wget -qO - https://download.sublimetext.com/sublimehq-pub.gpg | sudo apt-key add -
sudo apt-get install apt-transport-https
echo "deb https://download.sublimetext.com/ apt/stable/" | sudo tee /etc/apt/sources.list.d/sublime-text.list
sudo apt-get update
sudo apt-get --assume-yes install sublime-text

# Quicksynergy, to use mouse / keyboard w/ multiple computers at once
sudo apt-get --assume-yes install quicksynergy

# For xclip, also useful to add this line to bashrc: alias "copy=xclip -selection clipboard"
sudo apt-get --assume-yes install xclip 

# maybe: 
# sudo apt-get install snapd
# sudo snap install slack --classic
# (BUT: don't love snap packages, icon for slack seems to be borked.
# maybe just manual install this with dpkg or software manager or whatever.)


# Google Chrome (from https://www.ubuntuupdates.org/ppa/google_chrome)
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
# This might be shady - might create duplication of sources somehow.
# Also, this seems to be broken on current 16.04 (2017.08)
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt-get update
sudo apt-get --assume-yes install google-chrome-stable

# Inkscape
sudo add-apt-repository ppa:inkscape.dev/stable
sudo apt-get update
sudo apt-get --assume-yes install inkscape #--upgrade


# Blender, for rendering (specify version number??)
sudo apt-get --assume-yes install ffmpeg

# Needed for FSL to run correctly
sudo apt-get install libgcrypt11-dev zlib1g-dev
# NEED MPLAYER TOO FOR STIMULUS_PRESENTATION

# needs some more wrangling to be correct
# # Insync
# ## Get PPA for insync
# sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys ACCAF35C
# #Create this file:
# #vim /etc/apt/sources.list.d/insync.list
# #and add this line:
# #deb http://apt.insynchq.com/ubuntu xenial non-free contrib # FOR STANDARD UBUNTU
# #deb http://apt.insynchq.com/mint sarah non-free contrib # FOR LINUX MINT
# #replace 'ubuntu' with 'debian' or 'mint' as appropriate (for linux distribution)
# #replace 'xenial' with installed os (xenial = ubuntu 16.04)
# ## Update apt
# sudo apt-get update
# ## Install
# sudo apt-get --assume-yes install insync
