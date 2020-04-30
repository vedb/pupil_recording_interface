.. _api-reference:

API Reference
=============

Top-level functions and classes
-------------------------------

.. currentmodule:: pupil_recording_interface

I/O functions
.............

.. autosummary::
    :nosignatures:
    :toctree: _generated

    load_dataset
    write_netcdf
    load_info
    load_user_info
    get_gaze_mappers


Reader classes
..............

.. autosummary::
    :nosignatures:
    :toctree: _generated

    GazeReader
    OdometryReader
    VideoReader
    OpticalFlowReader


Device classes
..............

.. autosummary::
    :nosignatures:
    :toctree: _generated

    VideoDeviceUVC
    VideoDeviceFLIR
    RealSenseDeviceT265


Stream classes
..............

.. autosummary::
    :nosignatures:
    :toctree: _generated

    VideoStream
    MotionStream
    StreamManager


Process classes
...............

.. autosummary::
    :nosignatures:
    :toctree: _generated

    Pipeline
    VideoDisplay
    VideoRecorder
    PupilDetector
    GazeMapper
    CircleMarkerDetector
    Calibration
    CircleGridDetector
    CamParamEstimator
    MotionRecorder

.. TODO process, pipeline


Class member details
--------------------

.. toctree::
   :maxdepth: 1

   api/reader
   api/device
   api/stream
   api/process
