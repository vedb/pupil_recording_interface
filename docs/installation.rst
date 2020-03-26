Installation
============

Latest version
--------------

pupil_recording_interface can be installed via ``pip``:

.. code-block:: console

    $ pip install git+https://github.com/vedb/pupil_recording_interface.git

If you are using the conda package manager, install these dependencies first:

.. code-block:: console

    $ conda install xarray scipy msgpack-python opencv

Afterwards, install the package via ``pip`` as detailed above.

.. _optional_dependencies:

Optional dependencies
---------------------

Recording
.........

To record video from the pupil cameras, you need to install `ffmpeg`_ and the
`PyUVC`_ library.

Odometry data from an Intel RealSense T265 tracking camera can be recorded
by installing the `RealSense SDK`_ and ``pyrealsense``:

.. code-block:: console

    $ pip install pyrealsense2

.. note::

    If you didn't install PyUVC, you might also need to
    ``pip install monotonic``. The recorded timestamps for the odometry data
    are not guaranteed to be perfectly synchronized with timestamps recorded
    through Pupil Capture, however.

.. _ffmpeg: https://www.ffmpeg.org
.. _PyUVC: https://github.com/pupil-labs/pyuvc
.. _RealSense SDK: https://github.com/IntelRealSense/librealsense

Export
......

Install the ``netcdf4`` library in order to export data to the netCDF format:

.. code-block:: console

    $ pip install netcdf4
