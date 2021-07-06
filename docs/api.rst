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
    load_pldata
    save_pldata
    get_gaze_mappers
    load_object
    save_object
    get_test_recording


Other functions
...............

.. autosummary::
    :nosignatures:
    :toctree: _generated

    merge_pupils


Reader classes
..............

.. autosummary::
    :nosignatures:
    :toctree: _generated

    GazeReader
    MotionReader
    VideoReader
    OpticalFlowReader


Device classes
..............

.. autosummary::
    :nosignatures:
    :toctree: _generated
    :template: custom-class-template.rst
    :recursive:

    VideoDeviceUVC
    VideoDeviceFLIR
    RealSenseDeviceT265


Stream classes
..............

.. autosummary::
    :nosignatures:
    :toctree: _generated
    :template: custom-class-template.rst
    :recursive:

    VideoStream
    MotionStream
    StreamManager


Process classes
...............

.. autosummary::
    :nosignatures:
    :toctree: _generated
    :template: custom-class-template.rst
    :recursive:

    Pipeline
    VideoDisplay
    VideoRecorder
    PupilDetector
    GazeMapper
    CircleDetector
    Calibration
    CircleGridDetector
    CamParamEstimator
    MotionRecorder
    VideoFileSyncer


Class member details
--------------------

.. toctree::
   :maxdepth: 1

   api/reader
