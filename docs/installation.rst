Installation
============

Latest version
--------------

pupil_recording_interface can be installed via ``pip``:

.. code-block:: console

    pip install git+https://github.com/vedb/pupil_recording_interface.git

If you are using the conda package manager, install these dependencies first:

.. code-block:: console

    conda install numpy pandas xarray scipy msgpack-python opencv

Afterwards, install the package via ``pip`` as detailed above.

Optional dependencies
---------------------

Install the ``netcdf4`` library in order to export data to the netCDF format:

.. code-block:: console

    pip install netcdf4

Odometry data from an Intel RealSense T265 tracking camera can be recorded
by installing these packages:

.. code-block:: console

    pip install pyrealsense2 monotonic

Installing the `PyUVC`_ library will make sure that the timestamps of the
odometry recording are properly synchronized with those recorded through
Pupil Capture.
