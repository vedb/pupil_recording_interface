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


Interface classes
.................

.. autosummary::
    :nosignatures:
    :toctree: _generated

    GazeInterface
    OdometryInterface
    VideoInterface
    OpticalFlowInterface


Recorder classes
................

.. autosummary::
    :nosignatures:
    :toctree: _generated

    OdometryRecorder



Class member details
--------------------

GazeInterface
.............

I/O functions
~~~~~~~~~~~~~

.. autosummary::
    :nosignatures:
    :toctree: _generated

    GazeInterface.load_dataset
    GazeInterface.write_netcdf

OdometryInterface
.................

I/O functions
~~~~~~~~~~~~~

.. autosummary::
    :nosignatures:
    :toctree: _generated

    OdometryInterface.load_dataset
    OdometryInterface.write_netcdf


VideoInterface
..............

I/O functions
~~~~~~~~~~~~~

.. autosummary::
    :nosignatures:
    :toctree: _generated

    VideoInterface.load_frame
    VideoInterface.load_raw_frame
    VideoInterface.read_frames
    VideoInterface.load_timestamps
    VideoInterface.load_dataset
    VideoInterface.write_netcdf

Frame processing
~~~~~~~~~~~~~~~~

.. autosummary::
    :nosignatures:
    :toctree: _generated

    VideoInterface.convert_to_uint8
    VideoInterface.convert_color
    VideoInterface.get_roi
    VideoInterface.undistort_frame
    VideoInterface.subsample_frame
    VideoInterface.process_frame


OpticalFlowInterface
....................

See the parent `VideoInterface`_ class for additional methods.

I/O functions
~~~~~~~~~~~~~

.. autosummary::
    :nosignatures:
    :toctree: _generated

    OpticalFlowInterface.load_dataset
    OpticalFlowInterface.write_netcdf
    OpticalFlowInterface.load_optical_flow
    OpticalFlowInterface.read_optical_flow

Optical flow calculation
~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
    :nosignatures:
    :toctree: _generated

    OpticalFlowInterface.calculate_optical_flow



OdometryRecorder
................

.. autosummary::
    :nosignatures:
    :toctree: _generated

    OdometryRecorder.run
