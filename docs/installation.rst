Installation
============

Latest version
--------------

pupil_recording_interface can be installed via ``pip``:

.. code-block:: console

    $ pip install git+https://github.com/vedb/pupil_recording_interface.git

If you are using the conda package manager, install these dependencies first:

.. code-block:: console

    $ conda install xarray scipy opencv "msgpack-python<1.0"

Afterwards, install the package via ``pip``, but without dependencies:

.. code-block:: console

    $ pip install --no-deps git+https://github.com/vedb/pupil_recording_interface.git


.. _optional_dependencies:

Optional dependencies
---------------------

The library requires several optional dependencies for features like streaming
video from the Pupil Core cameras, recording data or special algorithms such as
pupil detection.

Many of these dependencies are non-trivial to install, especially on Windows.
Therefore, we recommend installing the library in a conda environment since
conda provides a straightforward way of cross-platform distribution for
non-Python dependencies. We are actively working on packaging those
dependencies that aren't already available through conda. At the moment, only
packages for Linux x64 and Python versions 3.6 and 3.7 are available.


Streaming
.........

To stream video from the pupil cameras you need to install the `PyUVC`_
library.

Linux
~~~~~

A conda package is available for Linux:

.. code-block:: console

    $ conda install -c phausamann -c conda-forge pyuvc

Set these udev rules to access the cameras as a normal user:

.. code-block:: console

    $ echo 'SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", GROUP="plugdev", MODE="0664"' | sudo tee /etc/udev/rules.d/10-libuvc.rules > /dev/null
    $ sudo udevadm trigger

Windows and MacOS
~~~~~~~~~~~~~~~~~

For these operating systems, follow the instructions on the `PyUVC`_ GitHub
page.

.. _PyUVC: https://github.com/pupil-labs/pyuvc


Recording
.........

To record video you need to install `ffmpeg`_. This can be done via conda on
all operating systems:

.. code-block:: console

    $ conda install ffmpeg x264

.. _ffmpeg: https://www.ffmpeg.org


Pupil detection
...............

Pupil detection is implemented based on Pupil Labs' `pupil-detectors`_
package.

.. _pupil-detectors: https://github.com/pupil-labs/pupil-detectors

Linux
~~~~~

A conda package is available for Linux:

.. code-block:: console

    conda install -c phausamann -c conda-forge pupil-detectors

Windows and MacOS
~~~~~~~~~~~~~~~~~

Install via pip:

.. code-block:: console

    pip install pupil-detectors

On MacOS, you will probably need to install some build dependencies. Please
refer to the `pupil-detectors`_ GitHub pages for details.


RealSense T265
..............

Motion and video data from an Intel RealSense T265 tracking camera can be
streamed by installing the `RealSense SDK`_ and ``pyrealsense``:

.. code-block:: console

    $ pip install pyrealsense2

Linux
~~~~~

The RealSense SDK can be installed on Linux through conda:

.. code-block:: console

    $ conda install -c phausamann librealsense2

Windows and MacOS
~~~~~~~~~~~~~~~~~

For these operating systems, follow the instructions on the `RealSense SDK`_
GitHub page.

.. _RealSense SDK: https://github.com/IntelRealSense/librealsense


FLIR cameras
............

Linux
~~~~~

A conda package of FLIR's `PySpin` library is available for Linux:

.. code-block:: console

    conda install -c phausamann -c conda-forge pyspin

Windows and MacOS
~~~~~~~~~~~~~~~~~

Download the latest `Spinnaker SDK`_.

.. _Spinnaker SDK: https://www.flir.com/products/spinnaker-sdk


Export
......

Install the ``netcdf4`` library in order to export data to the netCDF format:

.. code-block:: console

    $ pip install netcdf4

or with conda:

.. code-block:: console

    $ conda install netcdf4

.. note::

    Unfortunately, the ``netcdf4`` conda package seems to be incompatible with
    the ``pupil-detectors`` package built against our OpenCV package with
    ffmpeg 3.4 support. However, this is only an issue if you need support for
    FLIR cameras. In that case, we recommend installing ``netcdf4`` through
    pip.
