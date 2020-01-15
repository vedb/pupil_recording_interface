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
    VideoDeviceT265


Recorder and Encoder classes
.....................................

.. autosummary::
    :nosignatures:
    :toctree: _generated

    OdometryRecorder
    VideoRecorder
    VideoEncoder


Class member details
--------------------

GazeReader
.............

I/O functions
~~~~~~~~~~~~~

.. autosummary::
    :nosignatures:
    :toctree: _generated

    GazeReader.load_dataset
    GazeReader.write_netcdf

OdometryReader
.................

I/O functions
~~~~~~~~~~~~~

.. autosummary::
    :nosignatures:
    :toctree: _generated

    OdometryReader.load_dataset
    OdometryReader.write_netcdf


VideoReader
..............

I/O functions
~~~~~~~~~~~~~

.. autosummary::
    :nosignatures:
    :toctree: _generated

    VideoReader.load_frame
    VideoReader.load_raw_frame
    VideoReader.read_frames
    VideoReader.load_timestamps
    VideoReader.load_dataset
    VideoReader.write_netcdf

Frame processing
~~~~~~~~~~~~~~~~

.. autosummary::
    :nosignatures:
    :toctree: _generated

    VideoReader.convert_to_uint8
    VideoReader.convert_color
    VideoReader.get_roi
    VideoReader.undistort_frame
    VideoReader.subsample_frame
    VideoReader.process_frame


OpticalFlowReader
....................

See the parent `VideoReader`_ class for additional methods.

I/O functions
~~~~~~~~~~~~~

.. autosummary::
    :nosignatures:
    :toctree: _generated

    OpticalFlowReader.load_dataset
    OpticalFlowReader.write_netcdf
    OpticalFlowReader.load_optical_flow
    OpticalFlowReader.read_optical_flow

Optical flow calculation
~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
    :nosignatures:
    :toctree: _generated

    OpticalFlowReader.calculate_optical_flow


OdometryRecorder
................

.. autosummary::
    :nosignatures:
    :toctree: _generated

    OdometryRecorder.run


VideoRecorder
.............

.. autosummary::
    :nosignatures:
    :toctree: _generated

    VideoRecorder.run
