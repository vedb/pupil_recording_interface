video
=====

.. currentmodule:: pupil_recording_interface

VideoInterface
--------------

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
--------------------

See the parent `VideoInterface`_ class for additional methods.

I/O functions
~~~~~~~~~~~~~

.. autosummary::
    :nosignatures:
    :toctree: _generated

    OpticalFlowInterface.load_dataset
    OpticalFlowInterface.write_netcdf
    OpticalFlowInterface.get_optical_flow
    OpticalFlowInterface.estimate_optical_flow

Optical flow calculation
~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
    :nosignatures:
    :toctree: _generated

    OpticalFlowInterface.calculate_flow
