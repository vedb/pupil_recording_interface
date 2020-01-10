Usage
=====

.. currentmodule:: pupil_recording_interface

Loading recordings
------------------

pupil_recording_interface provides a simple interface for loading recordings
made with Pupil Capture into Python. Recordings are loaded as `xarray`_
Datasets which provide an elegant way of working with multi-dimensional
labelled data.

.. _xarray: https://xarray.pydata.org


Gaze
....

You can easily load recorded gaze data with:

.. doctest::

    >>> import pupil_recording_interface as pri
    >>> pri.load_dataset(pri.TEST_RECORDING, gaze='recording')
    <xarray.Dataset>
    Dimensions:             (cartesian_axis: 3, pixel_axis: 2, time: 5160)
    Coordinates:
      * time                (time) datetime64[ns] 2019-10-10T16:43:20.149777889 ... 2019-10-10T16:43:41.262381792
      * pixel_axis          (pixel_axis) <U1 'x' 'y'
      * cartesian_axis      (cartesian_axis) <U1 'x' 'y' 'z'
    Data variables:
        gaze_norm_pos       (time, pixel_axis) float64 0.4082 0.3912 ... 0.1286
        gaze_point          (time, cartesian_axis) float64 nan nan ... 0.1299
        gaze_confidence_3d  (time) float64 0.8787 0.8769 0.9233 ... 0.9528 0.9528

Here, ``pri.TEST_RECORDING`` is an alias for a folder included in the
package that includes a very short example recording. ``gaze='recording'``
tells the function to load the recorded gaze data. The dataset contains
three arrays, the two dimensional norm pos, the three-dimensional gaze point
and the confidence of the mapping. All arrays behave like numpy arrays, (i.e.
you can use functions like ``np.sum`` on them), but will preserve their
labels (called coordinates) in most cases.

If you performed post-hoc gaze mapping, it is also possible to reference an
offline gaze mapper by name and load its data:

.. doctest::

    >>> pri.load_dataset(pri.TEST_RECORDING, gaze='3d Gaze Mapper')
    <xarray.Dataset>
    Dimensions:             (cartesian_axis: 3, pixel_axis: 2, time: 5134)
    Coordinates:
      * time                (time) datetime64[ns] 2019-10-10T16:43:20.242571831 ... 2019-10-10T16:43:41.209933281
      * pixel_axis          (pixel_axis) <U1 'x' 'y'
      * cartesian_axis      (cartesian_axis) <U1 'x' 'y' 'z'
    Data variables:
        gaze_norm_pos       (time, pixel_axis) float64 0.4247 0.4144 ... 0.1215
        gaze_point          (time, cartesian_axis) float64 -0.01031 ... 0.09778
        gaze_confidence_3d  (time) float64 0.8977 0.8977 0.9281 ... 0.9002 0.8536

Finally, it is also possible to merge the data from a 2d and a 3d gaze
mapper, in which case the norm pos will come from the 2d mapper and the gaze
point from the 3d mapper:

.. doctest::

    >>> pri.load_dataset(pri.TEST_RECORDING,
    ...                  gaze={'2d': '2d Gaze Mapper ', '3d': '3d Gaze Mapper'})
    <xarray.Dataset>
    Dimensions:             (cartesian_axis: 3, pixel_axis: 2, time: 5134)
    Coordinates:
      * time                (time) datetime64[ns] 2019-10-10T16:43:20.242571831 ... 2019-10-10T16:43:41.209933281
      * pixel_axis          (pixel_axis) <U1 'x' 'y'
      * cartesian_axis      (cartesian_axis) <U1 'x' 'y' 'z'
    Data variables:
        gaze_norm_pos       (time, pixel_axis) float64 0.4586 0.5304 ... 1.072 2.01
        gaze_point          (time, cartesian_axis) float64 -0.01031 ... 0.09778
        gaze_confidence_2d  (time) float64 0.9428 0.929 0.9442 ... 0.9501 0.9268
        gaze_confidence_3d  (time) float64 0.8977 0.8977 0.9281 ... 0.9002 0.8536

You can get a set of all available gaze mappers for a recording with:

.. doctest::

    >>> pri.get_gaze_mappers(pri.TEST_RECORDING) # doctest:+SKIP
    {'2d Gaze Mapper ', '3d Gaze Mapper', 'recording'}


Loading videos
--------------

Since video data is rather large, we rarely bulk-load entire video
recordings (although it is possible, see `Other video functionality`_).
Rather, this library provides a :py:class:`VideoReader` class with which
we can go through videos frame by frame. You can get information about the
world camera video with:

.. doctest::

    >>> interface = pri.VideoReader(pri.TEST_RECORDING)
    >>> interface.video_info
    {'resolution': (1280, 720), 'frame_count': 504, 'fps': 23.987}

With :py:func:`VideoReader.load_raw_frame` you can retrieve a raw video
frame by index:

.. doctest::

    >>> interface = pri.VideoReader(pri.TEST_RECORDING)
    >>> frame = interface.load_raw_frame(100)
    >>> frame.shape
    (720, 1280, 3)

If you have the ``matplotlib`` library installed, you can show the frame
with ``imshow()``. Note that you have to reverse the last axis as the frame
is loaded as a BGR image but imshow expects RGB:

.. code-block:: python

    >>> import matplotlib.pyplot as plt
    >>> plt.imshow(frame[:, :, ::-1])

.. plot::

    import pupil_recording_interface as pri
    interface = pri.VideoReader(pri.TEST_RECORDING)
    frame = interface.load_raw_frame(100)

    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(12.8, 7.2))
    ax = plt.axes([0,0,1,1], frameon=False)
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.imshow(frame[:, :, ::-1])

ROI extraction
..............

You can easily extract an ROI around the current gaze point in the image by
specifying the ``norm_pos`` and ``roi_size`` parameters and using the
:py:func:`VideoReader.load_frame` method:

.. doctest::

    >>> gaze = pri.load_dataset(pri.TEST_RECORDING, gaze='2d Gaze Mapper ')
    >>> interface = pri.VideoReader(
    ...     pri.TEST_RECORDING, norm_pos=gaze.gaze_norm_pos, roi_size=64)
    >>> frame = interface.load_frame(100)
    >>> frame.shape
    (64, 64, 3)
    >>> plt.imshow(frame[:, :, ::-1]) # doctest:+SKIP

.. plot::

    import pupil_recording_interface as pri
    gaze = pri.load_dataset(pri.TEST_RECORDING, gaze='2d Gaze Mapper ')
    interface = pri.VideoReader(
        pri.TEST_RECORDING, norm_pos=gaze.gaze_norm_pos, roi_size=64)
    frame = interface.load_frame(100)

    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(3.2, 3.2))
    ax = plt.axes([0,0,1,1], frameon=False)
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.imshow(frame[:, :, ::-1])

Other frame processing
......................

Video frames can also be sub-sampled and converted to grayscale with the
``subsampling`` and ``color_format`` parameters:

.. doctest::

    >>> interface = pri.VideoReader(
    ...     pri.TEST_RECORDING, color_format='gray', subsampling=4.)
    >>> frame = interface.load_frame(100)
    >>> frame.shape
    (180, 320)

:py:func:`VideoReader.read_frames` provides a generator for frames that
can be restricted to an index range with the ``start`` and ``end`` parameters:

.. doctest::

    >>> interface = pri.VideoReader(pri.TEST_RECORDING)
    >>> interface.read_frames(start=100, end=200) # doctest:+ELLIPSIS
    <generator object VideoReader.read_frames at ...>


Other video functionality
.........................

Eye videos can be loaded by specifying the ``source`` parameter:

.. doctest::

    >>> interface = pri.VideoReader(pri.TEST_RECORDING, source='eye0')
    >>> frame = interface.load_raw_frame(100)
    >>> frame.shape
    (192, 192, 3)

The video interface also provides a :py:func:`VideoReader.load_dataset`
method. The method is rather slow as it has to load each frame individually.
You can provide ``start`` and ``end`` timestamps to specify the time frame
of the loaded data:

.. doctest::

    >>> interface = pri.VideoReader(pri.TEST_RECORDING, subsampling=8.)
    >>> interface.load_dataset(
    ...     start=interface.user_info['experiment_start'],
    ...     end=interface.user_info['experiment_end'])
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

    >>> pri.load_info(pri.TEST_RECORDING) # doctest:+NORMALIZE_WHITESPACE
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

    >>> pri.load_user_info(pri.TEST_RECORDING) # doctest:+NORMALIZE_WHITESPACE
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

    Make sure you have installed the necessary dependencies for data export
    (see :ref:`optional_dependencies`).

Recorded data can also directly be written to disk:

.. doctest::

    >>> pri.write_netcdf(
    ...    pri.TEST_RECORDING, gaze='recording', output_folder='.')

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
        gaze_norm_pos       (time, pixel_axis) float64 ...
        gaze_point          (time, cartesian_axis) float64 ...
        gaze_confidence_3d  (time) float64 ...

.. testcleanup::

    import os
    os.remove('gaze.nc')
