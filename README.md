# pupil_recording_interface
Python backend and cli for pupil recordings

## Installation

    $ pip install git+https://github.com/vedb/pupil_recording_interface.git
    
This will trigger a username/password prompt. Alternatively, if you have an
 ssh keypair set up:
 
    $ pip install git+ssh://git@github.com/vedb/pupil_recording_interface.git

## Usage

Export a pupil recording (gaze + odometry) to netCDF:

    import pupil_recording_interface as pri
    
    pri.export('/path/to/recording')
    
This will create `odometry.nc` and `gaze.nc` files in the `/path/to
/recording/exports` folder.