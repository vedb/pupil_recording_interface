.. _reading:

Reading data
============

.. currentmodule:: pupil_recording_interface

Loading recordings
------------------

pupil_recording_interface provides a simple interface for loading recordings
made with Pupil Capture into Python. Recordings are loaded as `xarray`_
Datasets which provide an elegant way of working with multi-dimensional
labeled data.

.. _xarray: https://xarray.pydata.org


Gaze
....

You can easily load recorded gaze data with:

.. doctest::

    >>> import pupil_recording_interface as pri
    >>> pri.load_dataset(pri.get_test_recording(), gaze='recording')
    <xarray.Dataset>
    Dimensions:             (cartesian_axis: 3, pixel_axis: 2, time: 5160)
    Coordinates:
      * time                (time) datetime64[ns] 2019-10-10T16:43:20.149777889 ... 2019-10-10T16:43:41.262381792
      * pixel_axis          (pixel_axis) <U1 'x' 'y'
      * cartesian_axis      (cartesian_axis) <U1 'x' 'y' 'z'
    Data variables:
        eye                 (time) int64 2 2 2 2 2 2 2 2 2 2 ... 2 2 2 2 2 2 2 2 2 2
        gaze_norm_pos       (time, pixel_axis) float64 0.4082 0.3912 ... 0.1286
        gaze_point          (time, cartesian_axis) float64 nan nan ... 0.1299
        eye0_center         (time, cartesian_axis) float64 nan nan ... -0.02006
        eye1_center         (time, cartesian_axis) float64 nan nan ... -0.02153
        eye0_normal         (time, cartesian_axis) float64 nan nan ... 0.267 0.9269
        eye1_normal         (time, cartesian_axis) float64 nan nan ... 0.1646 0.9797
        gaze_confidence_3d  (time) float64 0.8787 0.8769 0.9233 ... 0.9528 0.9528


Here, ``pri.get_test_recording()`` is an alias for a folder included in the
package that includes a very short example recording. ``gaze='recording'``
tells the function to load the recorded gaze data. The dataset contains
the following arrays:

* ``eye``: the eye data that produced the mapping, 0 for eye 0 (usually right),
  1 for eye 1 (usually left), 2 for binocular mapping
* ``gaze_norm_pos``: the two dimensional norm pos, i.e. the normalized position
  of the gaze in the video frame where (0, 0) is the lower left and (1, 1) is
  the upper right corner of the frame
* ``gaze_point``: the three-dimensional gaze point represented in the world
  camera coordinate system (x right, y down, z forward), in meters
* ``eye{0,1}_center``: the center of each eye represented in the world
  camera coordinate system, in meters
* ``eye{0,1}_normal``: the normal of each eye represented in the world
  camera coordinate system
* ``gaze_confidence_3d``: the confidence of the mapping between 0 and 1

All arrays behave like numpy arrays, (i.e. you can use functions like
``np.sum`` on them), but will preserve their labels (called coordinates) in
most cases.

If you performed post-hoc gaze mapping, it is also possible to reference an
offline gaze mapper by name and load its data:

.. doctest::

    >>> pri.load_dataset(pri.get_test_recording(), gaze='3d Gaze Mapper')
    <xarray.Dataset>
    Dimensions:             (cartesian_axis: 3, pixel_axis: 2, time: 5134)
    Coordinates:
      * time                (time) datetime64[ns] 2019-10-10T16:43:20.242571831 ... 2019-10-10T16:43:41.209933281
      * pixel_axis          (pixel_axis) <U1 'x' 'y'
      * cartesian_axis      (cartesian_axis) <U1 'x' 'y' 'z'
    Data variables:
        eye                 (time) int64 2 2 2 2 2 2 2 2 2 2 ... 2 2 2 2 2 2 2 2 2 2
        gaze_norm_pos       (time, pixel_axis) float64 0.4247 0.4144 ... 0.1215
        gaze_point          (time, cartesian_axis) float64 -0.01031 ... 0.09778
        eye0_center         (time, cartesian_axis) float64 0.02037 0.01459 ... -0.02
        eye1_center         (time, cartesian_axis) float64 -0.03989 ... -0.02
        eye0_normal         (time, cartesian_axis) float64 -0.2449 ... 0.9327
        eye1_normal         (time, cartesian_axis) float64 0.2435 ... 0.9696
        gaze_confidence_3d  (time) float64 0.8977 0.8977 0.9281 ... 0.9002 0.8536

Finally, it is also possible to merge the data from a 2d and a 3d gaze
mapper, in which case the norm pos will come from the 2d mapper and the gaze
point from the 3d mapper:

.. doctest::

    >>> pri.load_dataset(
    ...     pri.get_test_recording(), gaze={'2d': '2d Gaze Mapper ', '3d': '3d Gaze Mapper'}
    ... )
    <xarray.Dataset>
    Dimensions:             (cartesian_axis: 3, pixel_axis: 2, time: 5134)
    Coordinates:
      * time                (time) datetime64[ns] 2019-10-10T16:43:20.242571831 ... 2019-10-10T16:43:41.209933281
      * pixel_axis          (pixel_axis) <U1 'x' 'y'
      * cartesian_axis      (cartesian_axis) <U1 'x' 'y' 'z'
    Data variables:
        eye                 (time) int64 2 2 2 2 2 2 2 2 2 2 ... 2 2 2 2 2 2 2 2 2 2
        gaze_norm_pos       (time, pixel_axis) float64 0.4586 0.5304 ... 1.072 2.01
        gaze_point          (time, cartesian_axis) float64 -0.01031 ... 0.09778
        eye0_center         (time, cartesian_axis) float64 0.02037 0.01459 ... -0.02
        eye1_center         (time, cartesian_axis) float64 -0.03989 ... -0.02
        eye0_normal         (time, cartesian_axis) float64 -0.2449 ... 0.9327
        eye1_normal         (time, cartesian_axis) float64 0.2435 ... 0.9696
        gaze_confidence_2d  (time) float64 0.9428 0.929 0.9442 ... 0.9501 0.9268
        gaze_confidence_3d  (time) float64 0.8977 0.8977 0.9281 ... 0.9002 0.8536

You can get a set of all available gaze mappers for a recording with:

.. doctest::

    >>> pri.get_gaze_mappers(pri.get_test_recording()) # doctest:+SKIP
    {'2d Gaze Mapper ', '3d Gaze Mapper', 'recording'}


Loading videos
--------------

Since video data is rather large, we rarely bulk-load entire video
recordings (although it is possible, see `Other video functionality`_).
Rather, this library provides a :py:class:`VideoReader` class with which
we can go through videos frame by frame. You can get information about the
world camera video with:

.. doctest::

    >>> reader = pri.VideoReader(pri.get_test_recording())
    >>> reader.video_info
    {'resolution': (1280, 720), 'frame_count': 504, 'fps': 23.987}

With :py:func:`VideoReader.load_raw_frame` you can retrieve a raw video
frame by index:

.. doctest::

    >>> reader = pri.VideoReader(pri.get_test_recording())
    >>> frame = reader.load_raw_frame(100)
    >>> frame.shape
    (720, 1280, 3)

or by timestamp:

.. doctest::

    >>> reader = pri.VideoReader(pri.get_test_recording())
    >>> frame = reader.load_raw_frame(reader.timestamps[100])
    >>> frame.shape
    (720, 1280, 3)

Here, we used the ``timestamps`` attribute of the reader which contains the
timestamps for each frame to get the timestamp of the frame with index 100.

If you have the ``matplotlib`` library installed, you can show the frame
with ``imshow()``. Note that you have to reverse the last axis as the frame
is loaded as a BGR image but imshow expects RGB:

.. code-block:: python

    >>> import matplotlib.pyplot as plt
    >>> plt.imshow(frame[:, :, ::-1])

.. plot::

    import pupil_recording_interface as pri
    reader = pri.VideoReader(pri.get_test_recording())
    frame = reader.load_raw_frame(100)

    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(12.8, 7.2))
    ax = plt.axes([0,0,1,1], frameon=False)
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.imshow(frame[:, :, ::-1])

Eye videos can be loaded by specifying the ``stream`` parameter:

.. doctest::

    >>> eye_reader = pri.VideoReader(pri.get_test_recording(), stream='eye0')

With ``return_timestamp=True`` you can get the corresponding timestamp for a
frame:

.. doctest::

    >>> timestamp, frame = eye_reader.load_frame(100, return_timestamp=True)
    >>> timestamp
    Timestamp('2019-10-10 16:43:21.087194920')

This timestamp can now be used to get the closest world video frame:

.. doctest::

    >>> frame = reader.load_frame(timestamp)
    >>> frame.shape
    (720, 1280, 3)

ROI extraction
..............

You can easily extract an ROI around the current gaze point in the image by
specifying the ``norm_pos`` and ``roi_size`` parameters and using the
:py:func:`VideoReader.load_frame` method:

.. doctest::

    >>> gaze = pri.load_dataset(pri.get_test_recording(), gaze='2d Gaze Mapper ')
    >>> reader = pri.VideoReader(
    ...     pri.get_test_recording(), norm_pos=gaze.gaze_norm_pos, roi_size=64
    ... )
    >>> frame = reader.load_frame(100)
    >>> frame.shape
    (64, 64, 3)
    >>> plt.imshow(frame[:, :, ::-1]) # doctest:+SKIP

.. plot::

    import pupil_recording_interface as pri
    gaze = pri.load_dataset(pri.get_test_recording(), gaze='2d Gaze Mapper ')
    reader = pri.VideoReader(
        pri.get_test_recording(), norm_pos=gaze.gaze_norm_pos, roi_size=64
    )
    frame = reader.load_frame(100)

    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(3.2, 3.2))
    ax = plt.axes([0,0,1,1], frameon=False)
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.imshow(frame[:, :, ::-1])


Other video functionality
.........................

Video frames can also be sub-sampled and converted to grayscale with the
``subsampling`` and ``color_format`` parameters:

.. doctest::

    >>> reader = pri.VideoReader(
    ...     pri.get_test_recording(), color_format='gray', subsampling=4.
    ... )
    >>> frame = reader.load_frame(100)
    >>> frame.shape
    (180, 320)

:py:func:`VideoReader.read_frames` provides a generator for frames that
can be restricted to an index or timestamp range with the ``start`` and ``end``
parameters:

.. doctest::

    >>> reader = pri.VideoReader(pri.get_test_recording())
    >>> reader.read_frames(start=100, end=200) # doctest:+ELLIPSIS
    <generator object VideoReader.read_frames at ...>

The video reader also provides a :py:func:`VideoReader.load_dataset`
method. The method is rather slow as it has to load each frame individually.
You can provide ``start`` and ``end`` timestamps to specify the time frame
of the loaded data:

.. doctest::

    >>> reader = pri.VideoReader(pri.get_test_recording(), subsampling=8.)
    >>> reader.load_dataset(
    ...     start=reader.user_info['experiment_start'],
    ...     end=reader.user_info['experiment_end'],
    ... )
    <xarray.Dataset>
    Dimensions:  (color: 3, frame_x: 160, frame_y: 90, time: 22)
    Coordinates:
      * time     (time) datetime64[ns] 2019-10-10T16:43:23.237552881 ... 2019-10-10T16:43:24.175843954
      * frame_x  (frame_x) int64 0 1 2 3 4 5 6 7 ... 152 153 154 155 156 157 158 159
      * frame_y  (frame_y) int64 0 1 2 3 4 5 6 7 8 9 ... 81 82 83 84 85 86 87 88 89
      * color    (color) <U1 'B' 'G' 'R'
    Data variables:
        frames   (time, frame_y, frame_x, color) uint8 8 7 23 9 8 21 ... 5 11 9 7 21

Recording metadata
------------------

The recording metadata file created by Pupil Capture can be loaded with:

.. doctest::

    >>> pri.load_info(pri.get_test_recording()) # doctest:+NORMALIZE_WHITESPACE
    {'duration_s': 21.0,
     'meta_version': '2.0',
     'min_player_version': '1.16',
     'recording_name': '2019_10_10',
     'recording_software_name': 'Pupil Capture',
     'recording_software_version': '1.16.95',
     'recording_uuid': 'e5059604-26f1-42ed-8e35-354198b56021',
     'start_time_synced_s': 2294.807856069,
     'start_time_system_s': 1570725800.220913,
     'system_info': 'User: test_user, Platform: Linux'}

You can also load the user info with:

.. doctest::

    >>> pri.load_user_info(pri.get_test_recording()) # doctest:+NORMALIZE_WHITESPACE
    {'name': 'TEST',
     'pre_calibration_start': Timestamp('2019-10-10 16:43:21.220912933'),
     'pre_calibration_end': Timestamp('2019-10-10 16:43:22.220912933'),
     'experiment_start': Timestamp('2019-10-10 16:43:23.220912933'),
     'experiment_end': Timestamp('2019-10-10 16:43:24.220912933'),
     'post_calibration_start': Timestamp('2019-10-10 16:43:25.220912933'),
     'post_calibration_end': Timestamp('2019-10-10 16:43:26.220912933'),
     'height': 1.8}

Data export
-----------

.. note::

    Make sure you have installed the necessary
    :ref:`dependencies for data export<optional_dependencies>`.

Recorded data can also directly be written to disk:

.. doctest::

    >>> pri.write_netcdf(
    ...    pri.get_test_recording(), gaze='recording', output_folder='.'
    ... )

This will create a ``gaze.nc`` file in the current folder. This file type can
directly be loaded by xarray which is a lot faster than the
:py:func:`load_dataset` function:

.. doctest::

    >>> import xarray as xr
    >>> xr.open_dataset('gaze.nc')
    <xarray.Dataset>
    Dimensions:             (cartesian_axis: 3, pixel_axis: 2, time: 5160)
    Coordinates:
      * time                (time) datetime64[ns] 2019-10-10T16:43:20.149777889 ... 2019-10-10T16:43:41.262381792
      * pixel_axis          (pixel_axis) object 'x' 'y'
      * cartesian_axis      (cartesian_axis) object 'x' 'y' 'z'
    Data variables:
        eye                 (time) float64 ...
        gaze_norm_pos       (time, pixel_axis) float64 ...
        gaze_point          (time, cartesian_axis) float64 ...
        eye0_center         (time, cartesian_axis) float64 ...
        eye1_center         (time, cartesian_axis) float64 ...
        eye0_normal         (time, cartesian_axis) float64 ...
        eye1_normal         (time, cartesian_axis) float64 ...
        gaze_confidence_3d  (time) float64 ...

.. testcleanup::

    import os
    os.remove('gaze.nc')
