Installation
============

Latest version
--------------

pupil_recording_interface can be installed via ``pip``:

.. code-block:: console

    $ pip install opencv-python git+https://github.com/vedb/pupil_recording_interface.git

or via ``conda`` from our own channel:

.. code-block:: console

    $ conda install -c vedb -c conda-forge pupil_recording_interface


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


.. _example_dependencies:

Example data
............

To download the test recording used in the examples you need to install pooch:

.. code-block:: console

    $ pip install pooch

or:

.. code-block:: console

    $ conda install pooch


.. _streaming_dependencies:

Streaming
.........

To stream video from the pupil cameras you need to install the `PyUVC`_
library.

Linux
~~~~~

A conda package is available for Linux:

.. code-block:: console

    $ conda install -c vedb -c conda-forge pyuvc

Set these udev rules to access the cameras as a normal user:

.. code-block:: console

    $ echo 'SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", GROUP="plugdev", MODE="0664"' | sudo tee /etc/udev/rules.d/10-libuvc.rules > /dev/null
    $ sudo udevadm trigger

Windows and MacOS
~~~~~~~~~~~~~~~~~

For these operating systems, follow the instructions on the `PyUVC`_ GitHub
page.

.. _PyUVC: https://github.com/pupil-labs/pyuvc


.. _recording_dependencies:

Recording
.........

To record video you need to install `ffmpeg`_. This can be done via conda on
all operating systems:

.. code-block:: console

    $ conda install ffmpeg x264

.. _ffmpeg: https://www.ffmpeg.org


H.265 encoding (Linux)
~~~~~~~~~~~~~~~~~~~~~~

On Linux it is also possible to record videos using the H.265/HEVC standard.
The ``x265`` implementation of the codec can be installed via conda along
with an ``ffmpeg`` package build with support for the library:

.. code-block:: console

    $ conda install -c loopbio ffmpeg x265

If you also need support for FLIR cameras (see :ref:`flir_dependencies`), you
will need to install our own ``ffmpeg`` package instead:

.. code-block:: console

    $ conda install -c loopbio -c vedb ffmpeg=3.4.2 x265


.. _pupil_detection_dependencies:

Pupil detection
...............

Pupil detection is implemented based on Pupil Labs' `pupil-detectors`_
package.

.. _pupil-detectors: https://github.com/pupil-labs/pupil-detectors

Linux
~~~~~

A conda package is available for Linux:

.. code-block:: console

    $ conda install -c vedb -c conda-forge pupil-detectors

Windows and MacOS
~~~~~~~~~~~~~~~~~

Install via pip:

.. code-block:: console

    $ pip install pupil-detectors

On MacOS, you will probably need to install some build dependencies. Please
refer to the `pupil-detectors`_ GitHub pages for details.


.. _realsense_dependencies:

RealSense T265
..............

Motion and video data from an Intel RealSense T265 tracking camera can be
streamed by installing the `RealSense SDK`_ and ``pyrealsense2``:

.. code-block:: console

    $ pip install pyrealsense2

Linux and MacOS
~~~~~~~~~~~~~~~

The RealSense SDK can be installed through conda:

.. code-block:: console

    $ conda install -c conda-forge librealsense

Windows
~~~~~~~

Follow the instructions on the `RealSense SDK`_ GitHub page.

.. _RealSense SDK: https://github.com/IntelRealSense/librealsense


.. _flir_dependencies:

FLIR cameras
............

``PySpin`` and ``simple-pyspin`` are required for FLIR camera support.

Linux
~~~~~

We provide a ``simple-pyspin`` conda package with all dependencies for Linux:

.. code-block:: console

    $ conda install -c vedb -c conda-forge simple-pyspin

Windows and MacOS
~~~~~~~~~~~~~~~~~

For ``PySpin`` download the latest `Spinnaker SDK`_.

.. _Spinnaker SDK: https://www.flir.com/products/spinnaker-sdk

``simple-pyspin`` can be installed via ``pip``:

.. code-block:: console

    $ pip install simple-pyspin


.. _export_dependencies:

Export
......

Install the ``netcdf4`` library in order to export data to the netCDF format:

.. code-block:: console

    $ pip install netcdf4

or with conda:

.. code-block:: console

    $ conda install netcdf4
