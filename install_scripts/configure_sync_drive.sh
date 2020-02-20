# Configure new user on POMlab computer

# First argument is drive on which to put sync folder

if [ $# -eq 0 ]
then
	export SYNC_DRIVE=/hdd01
else
    export SYNC_DRIVE=$1
fi

export USER_SYNC=$SYNC_DRIVE/$USER"_sync"
echo $USER_SYNC

if [ ! -d $USER_SYNC ]
then
	echo "Creating the directory "$USER_SYNC
	sudo mkdir -p $USER_SYNC
else
	echo "Directory already exists: "$USER_SYNC
fi

ln -s $USER_SYNC/lab ~/lab
ln -s $USER_SYNC/space ~/space


# Create useful functions to mount shared lab directories in user bashrc file

echo "pomlab(){" >> ~/.bashrc
echo "	sudo mount -t cifs //storage.unr.edu/cbs\\" >> ~/.bashrc
echo "	 /pomlab -o username=\$1,rw,domain=unr,uid=1000,gid=1000" >> ~/.bashrc
echo "}" >> ~/.bashrc

echo "pomspace(){" >> ~/.bashrc
echo "    sudo mount -t cifs //space.rc.unr.edu/assoc/pomlab\\" >> ~/.bashrc
echo "     /pomspace -o username=\$1,rw,domain=unr,uid=1000,gid=1000,vers=2.1" >> ~/.bashrc
echo "}" >> ~/.bashrc

echo "phuser(){" >> ~/.bashrc
echo "    sudo mount -t cifs //space.rc.unr.edu/home/\$1\\">> ~/.bashrc
echo "     /phuser -o username=\$1,rw,domain=unr,uid=1000,gid=1000,vers=2.1" >> ~/.bashrc
echo "}" >> ~/.bashrc

echo "vedb(){" >> ~/.bashrc
echo "    sudo mount -t cifs //space.rc.unr.edu/assoc/\\">> ~/.bashrc
echo "     /vedb -o username=\$1,rw,domain=unr,uid=1000,gid=1000,vers=2.1" >> ~/.bashrc
echo "}" >> ~/.bashrc

echo "set_pomspace_permission(){" >> ~/.bashrc
echo "    ssh $1@pronghorn.rc.unr.edu \"echo 'Setting permissions for $2...'; cd /data/gpfs/assoc/pomlab/; chmod -R g+w $2; echo 'Done'\"" >> ~/.bashrc
echo "}" >> ~/.bashrc

# Allow copying to clipboard: <somecommand> | copy
echo 'alias copy="xclip -selection clipboard"' >> ~/.bashrc

# Blender aliases
echo "alias bpython28='/opt/blender/blender-2.80-linux-glibc217-x86_64/2.80/python/bin/python3.7m'" >> ~/.bashrc
echo "alias blender28='/opt/blender/blender-2.80-linux-glibc217-x86_64/blender'" >> ~/.bashrc

# Set up FSL:
#FSLDIR="/auto/k2/share/fsl"
#. ${FSLDIR}/etc/fslconf/fsl.sh
#PATH=${FSLDIR}/bin:${PATH}
#export FSLDIR PATH

# Freesurfer run environment, from AH's code: 
echo "export FREESURFER_HOME=/usr/local/freesurfer" >> ~/.bashrc
echo "export SUBJECTS_DIR=$USER_SYNC/space/freesurfer_subjects/" >> ~/.bashrc
echo "source \$FREESURFER_HOME/SetUpFreeSurfer.sh" >> ~/.bashrc

# Because the philips scanner is very annoying
echo "export FS_LOAD_DWI=0" >> ~/.bashrc


# Config files for:
# vm_tools
# pycortex
# docdb_lite
# bvp
# cottoncandy
# docdb
