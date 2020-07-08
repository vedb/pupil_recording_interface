Additional features
===================

Head tracking (Odometry)
------------------------

The package also includes a mechanism for loading head
tracking data from an Intel RealSense T265 tracking camera attached to the
Pupil Core system. Head tracking data is referred to as odometry throughout
the package as it includes positions and velocities.

Loading
.......

Recorded odometry data can be loaded the same way as gaze data:

.. doctest::

    >>> import pupil_recording_interface as pri
    >>> pri.load_dataset(pri.TEST_RECORDING, odometry='recording')
    <xarray.Dataset>
    Dimensions:           (cartesian_axis: 3, quaternion_axis: 4, time: 4220)
    Coordinates:
      * time              (time) datetime64[ns] 2019-10-10T16:43:20.287212849 ... 2019-10-10T16:43:41.390241861
      * cartesian_axis    (cartesian_axis) <U1 'x' 'y' 'z'
      * quaternion_axis   (quaternion_axis) <U1 'w' 'x' 'y' 'z'
    Data variables:
        position          (time, cartesian_axis) float64 -0.1463 0.2765 ... 0.001237
        linear_velocity   (time, cartesian_axis) float64 0.001013 ... 0.004487
        angular_velocity  (time, cartesian_axis) float64 -0.01463 ... -0.008532
        confidence        (time) int64 3 3 3 3 3 3 3 3 3 3 3 ... 3 3 3 3 3 3 3 3 3 3
        orientation       (time, quaternion_axis) float64 0.004093 ... 0.06829


The dataset contains linear and angular position, linear and angular
velocity as well as the confidence of the tracking.


Optical flow
------------

:py:class:`OpticalFlowReader` is a subclass of :py:class:`VideoReader`
that provides methods for calculating optical flow between consecutive frames:

.. doctest::

    >>> reader = pri.OpticalFlowReader(pri.TEST_RECORDING, subsampling=8.)
    >>> reader.load_dataset(
    ...     start=reader.user_info['experiment_start'],
    ...     end=reader.user_info['experiment_end'],
    ... )
    <xarray.Dataset>
    Dimensions:       (pixel_axis: 2, roi_x: 160, roi_y: 90, time: 22)
    Coordinates:
      * time          (time) datetime64[ns] 2019-10-10T16:43:23.237552881 ... 2019-10-10T16:43:24.175843954
      * pixel_axis    (pixel_axis) <U1 'x' 'y'
      * roi_x         (roi_x) float64 -636.0 -628.0 -620.0 ... 620.0 628.0 636.0
      * roi_y         (roi_y) float64 356.0 348.0 340.0 ... -340.0 -348.0 -356.0
    Data variables:
        optical_flow  (time, roi_y, roi_x, pixel_axis) float64 nan nan ... 7.908e-11

.. note::

    For more details on this class please refer to the :ref:`api-reference`
    section.
