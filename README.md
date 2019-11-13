# pupil_recording_interface

Python backend and cli for pupil recordings

## Installation

    $ pip install git+https://github.com/vedb/pupil_recording_interface.git@py27-compat
    
This will trigger a username/password prompt. Alternatively, if you have an
 ssh keypair set up:
 
    $ pip install git+ssh://git@github.com/vedb/pupil_recording_interface.git@py27-compat

## Usage

Export gaze data to netCDF:

    import pupil_recording_interface as pri
    
    pri.write_netcdf('/path/to/recording', gaze='recording)
    
This will create a `gaze.nc` file in the `/path/to /recording/exports`
folder.

Load gaze and odometry data as xarray datasets:

    import pupil_recording_interface as pri
    
    gaze, odometry = pri.load_dataset('/path/to/recording', gaze='recording', odometry='recording')
