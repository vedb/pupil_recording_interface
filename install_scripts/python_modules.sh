# Install python & python modules

# Python
sudo apt-get install python3-dev
sudo apt-get install python3-pip
sudo -H pip3 install --upgrade pip
sudo -H pip3 install --upgrade ipython

# # Legacy python
# sudo apt-get install python-dev
# sudo apt-get install pip
# sudo -H pip install --upgrade pip
# sudo -H pip install --upgrade ipython

# Install all modules listed in python_modules.txt
while read MODULE
do
    # python 3
    sudo -H pip3 install $MODULE
    echo $MODULE
    # python 2
    #sudo -H pip install $MODULE
done < python_modules.txt


# for python 2 kernel in jupyter
#python2 -m pip install ipykernel
#python2 -m ipykernel install --user

# Set up jupyter notebook config
# From here: http://jupyter-notebook.readthedocs.io/en/stable/public_server.html

# Generate .key and .pem certificate files with open SSL for security
mkdir $HOME/.openssl/
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout $HOME/.openssl/notebook_key.key -out $HOME/.openssl//notebook_certification.pem

# Set up configuration file for jupyter
jupyter notebook --generate-config

# Set password for notebook
jupyter notebook password

# TO DO

# Copy nbserver file

# Copy password to nbconfig file

# OpenCV (cv2)

# Cuda libraries: tensorflow, pytorch