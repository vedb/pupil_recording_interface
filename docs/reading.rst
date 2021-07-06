.. _reading:

Reading data
============

.. currentmodule:: pupil_recording_interface

.. note::

    Make sure that you have installed the necessary
    :ref:`dependencies for running the examples<example_dependencies>`.

Loading recordings
------------------

pupil_recording_interface provides a simple interface for loading recordings
made with Pupil Capture into Python. Recordings are loaded as `xarray`_
Datasets which provide an elegant way of working with multi-dimensional
labeled data.

.. _xarray: https://xarray.pydata.org

To get started, we use :py:func:`get_test_recording` to download and cache a
very short example recording. The method returns the path to the cached folder:

.. doctest::

    >>> import pupil_recording_interface as pri
    >>> folder = pri.get_test_recording()

Gaze
....

You can easily load recorded gaze data with :py:meth:`load_gaze`:

.. doctest::

    >>> pri.load_gaze(folder)
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

The gaze dataset contains the following arrays:

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

    >>> pri.load_gaze(folder, source='3d Gaze Mapper')
    <xarray.Dataset>
    Dimensions:             (cartesian_axis: 3, pixel_axis: 2, time: 5125)
    Coordinates:
      * time                (time) datetime64[ns] 2019-10-10T16:43:20.278882265 ... 2019-10-10T16:43:41.209933281
      * pixel_axis          (pixel_axis) <U1 'x' 'y'
      * cartesian_axis      (cartesian_axis) <U1 'x' 'y' 'z'
    Data variables:
        eye                 (time) int64 2 2 2 2 2 2 2 2 2 2 ... 2 2 2 2 2 2 2 2 2 2
        gaze_norm_pos       (time, pixel_axis) float64 0.551 -0.2074 ... -0.07305
        gaze_point          (time, cartesian_axis) float64 0.003464 ... 0.03572
        eye0_center         (time, cartesian_axis) float64 0.005147 ... -0.02
        eye1_center         (time, cartesian_axis) float64 -0.04123 ... -0.02
        eye0_normal         (time, cartesian_axis) float64 -0.252 ... 0.9327
        eye1_normal         (time, cartesian_axis) float64 0.8417 -0.1958 ... 0.8089
        gaze_confidence_3d  (time) float64 0.9761 0.9586 0.9473 ... 0.9487 0.9207

Finally, it is also possible to merge the data from a 2d and a 3d gaze
mapper, in which case the norm pos will come from the 2d mapper and the gaze
point from the 3d mapper:

.. doctest::

    >>> pri.load_gaze(
    ...     folder, source={'2d': '2d Gaze Mapper ', '3d': '3d Gaze Mapper'}
    ... )
    <xarray.Dataset>
    Dimensions:             (cartesian_axis: 3, pixel_axis: 2, time: 4987)
    Coordinates:
      * time                (time) datetime64[ns] 2019-10-10T16:43:20.278882265 ... 2019-10-10T16:43:41.209933281
      * pixel_axis          (pixel_axis) <U1 'x' 'y'
      * cartesian_axis      (cartesian_axis) <U1 'x' 'y' 'z'
    Data variables:
        eye                 (time) int64 2 2 2 2 2 2 2 2 2 2 ... 2 2 2 2 2 2 2 2 2 2
        gaze_norm_pos       (time, pixel_axis) float64 0.4303 0.3921 ... 0.1736
        gaze_point          (time, cartesian_axis) float64 0.003464 ... 0.03572
        eye0_center         (time, cartesian_axis) float64 0.005147 ... -0.02
        eye1_center         (time, cartesian_axis) float64 -0.04123 ... -0.02
        eye0_normal         (time, cartesian_axis) float64 -0.252 ... 0.9327
        eye1_normal         (time, cartesian_axis) float64 0.8417 -0.1958 ... 0.8089
        gaze_confidence_2d  (time) float64 0.9761 0.9586 0.9473 ... 0.9487 0.9207
        gaze_confidence_3d  (time) float64 0.9761 0.9586 0.9473 ... 0.9487 0.9207

We can get a set of all available gaze mappers for a recording with:

.. doctest::

    >>> pri.get_gaze_mappers(folder) # doctest:+SKIP
    {'2d Gaze Mapper ', '3d Gaze Mapper', 'recording'}


Pupils
......

Pupil data can be loaded in a similar manner with :py:meth:`load_pupils`.
Since the recorded pupil data in the example recording uses the 3d pupil
detector, we need to specify ``method="3d"``:

.. doctest::

    >>> pri.load_pupils(folder, method="3d")
    <xarray.Dataset>
    Dimensions:                  (cartesian_axis: 3, pixel_axis: 2, time: 5170)
    Coordinates:
      * time                     (time) datetime64[ns] 2019-10-10T16:43:20.188713789 ... 2019-10-10T16:43:41.300101757
      * pixel_axis               (pixel_axis) <U1 'x' 'y'
      * cartesian_axis           (cartesian_axis) <U1 'x' 'y' 'z'
    Data variables:
        eye                      (time) int64 1 0 1 0 1 0 1 0 1 ... 1 0 1 0 1 0 1 0
        confidence               (time) float64 0.9374 0.9412 0.9036 ... 1.0 0.9771
        diameter                 (time) float64 49.14 43.71 49.01 ... 47.23 39.66
        ellipse_angle            (time) float64 61.4 85.65 61.37 ... 53.67 76.26
        pupil_norm_pos           (time, pixel_axis) float64 0.2423 0.663 ... 0.4504
        ellipse_center           (time, pixel_axis) float64 46.52 64.7 ... 105.5
        ellipse_axes             (time, pixel_axis) float64 42.82 49.14 ... 39.66
        circle_center            (time, cartesian_axis) float64 -5.992 ... 81.2
        circle_normal            (time, cartesian_axis) float64 -0.1717 ... -0.9904
        sphere_center            (time, cartesian_axis) float64 -3.931 ... 93.08
        projected_sphere_center  (time, pixel_axis) float64 67.58 101.9 ... 93.74
        projected_sphere_axes    (time, pixel_axis) float64 173.5 173.5 ... 159.9
        diameter_3d              (time) float64 5.928 5.864 5.913 ... 5.876 5.194
        theta                    (time) float64 1.175 1.993 1.174 ... 1.354 1.704
        phi                      (time) float64 -1.758 -1.533 ... -1.691 -1.534
        model_confidence         (time) float64 0.5911 0.851 ... 0.1845 0.6902
        circle_radius            (time) float64 2.964 2.932 2.956 ... 2.938 2.597
        sphere_radius            (time) float64 12.0 12.0 12.0 ... 12.0 12.0 12.0
        projected_sphere_angle   (time) float64 90.0 90.0 90.0 ... 90.0 90.0 90.0
        model_birth_timestamp    (time) float64 2.286e+03 2.284e+03 ... 2.284e+03


It is also possible to load pupil data that was computed post-hoc by
specifying ``source="offline"``. The post-hoc data contains 2d pupil data which
we can load with ``method="2d"``:

.. doctest::

    >>> pri.load_pupils(folder, source="offline", method="2d")
    <xarray.Dataset>
    Dimensions:         (pixel_axis: 2, time: 5164)
    Coordinates:
      * time            (time) datetime64[ns] 2019-10-10T16:43:20.277472973 ... 2019-10-10T16:43:41.364654779
      * pixel_axis      (pixel_axis) <U1 'x' 'y'
    Data variables:
        eye             (time) int64 1 0 1 0 1 0 1 0 1 0 1 ... 0 1 0 1 0 1 0 1 0 1 0
        confidence      (time) float64 0.9622 0.99 0.9273 0.9674 ... 0.99 0.99 0.0
        diameter        (time) float64 49.46 44.2 49.62 44.2 ... 39.84 47.64 0.0
        ellipse_angle   (time) float64 62.86 77.64 61.91 78.05 ... 83.34 124.2 -90.0
        pupil_norm_pos  (time, pixel_axis) float64 0.242 0.6634 0.5005 ... 0.0 1.0
        ellipse_center  (time, pixel_axis) float64 46.46 64.62 96.1 ... 0.0 0.0
        ellipse_axes    (time, pixel_axis) float64 43.06 49.46 39.78 ... 0.0 0.0


Calibration markers
...................

Locations of calibration markers that were detected post-hoc can be loaded
with :py:meth:`load_markers`:

.. doctest::

    >>> pri.load_markers(folder)
    <xarray.Dataset>
    Dimensions:      (pixel_axis: 2, time: 240)
    Coordinates:
      * time         (time) datetime64[ns] 2019-10-10T16:43:20.238371849 ... 2019-10-10T16:43:41.232636929
      * pixel_axis   (pixel_axis) <U1 'x' 'y'
    Data variables:
        frame_index  (time) int64 0 1 3 4 90 91 92 ... 427 428 429 430 431 513 540
        location     (time, pixel_axis) float64 202.4 258.9 202.8 ... 822.5 598.0


Caching
.......

.. note::

    This functionality requires the ``netcdf4`` library, see the
    :ref:`dependencies for data export<export_dependencies>`.

All of the above methods accept a ``cache`` argument that will cache the loaded
data in the netCDF format, making subsequent loading significantly faster:

    >>> pri.load_gaze(folder, cache=True)
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

.. testcode::
    :hide:

    import shutil
    shutil.rmtree(folder / "cache")

Loading videos
--------------

Since video data is rather large, we rarely bulk-load entire video
recordings (although it is possible, see `Other video functionality`_).
Rather, this library provides a :py:class:`VideoReader` class with which
we can go through videos frame by frame. You can get information about the
world camera video with:

.. doctest::

    >>> reader = pri.VideoReader(folder)
    >>> reader.video_info
    {'resolution': (1280, 720), 'frame_count': 504, 'fps': 23.987}

With :py:func:`VideoReader.load_raw_frame` you can retrieve a raw video
frame by index:

.. doctest::

    >>> reader = pri.VideoReader(folder)
    >>> frame = reader.load_raw_frame(100)
    >>> frame.shape
    (720, 1280, 3)

or by timestamp:

.. doctest::

    >>> reader = pri.VideoReader(folder)
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

    >>> eye_reader = pri.VideoReader(folder, stream='eye0')

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

    >>> gaze = pri.load_dataset(folder, gaze='2d Gaze Mapper ')
    >>> reader = pri.VideoReader(
    ...     folder, norm_pos=gaze.gaze_norm_pos, roi_size=64
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
    ...     folder, color_format='gray', subsampling=4.
    ... )
    >>> frame = reader.load_frame(100)
    >>> frame.shape
    (180, 320)

:py:func:`VideoReader.read_frames` provides a generator for frames that
can be restricted to an index or timestamp range with the ``start`` and ``end``
parameters:

.. doctest::

    >>> reader = pri.VideoReader(folder)
    >>> reader.read_frames(start=100, end=200) # doctest:+ELLIPSIS
    <generator object VideoReader.read_frames at ...>

The video reader also provides a :py:func:`VideoReader.load_dataset`
method. The method is rather slow as it has to load each frame individually.
You can provide ``start`` and ``end`` timestamps to specify the time frame
of the loaded data:

.. doctest::

    >>> reader = pri.VideoReader(folder, subsampling=8.)
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

    >>> pri.load_info(folder) # doctest:+NORMALIZE_WHITESPACE
    {'duration_s': 21.111775958999715,
     'meta_version': '2.3',
     'min_player_version': '2.0',
     'recording_name': '2019_10_10',
     'recording_software_name': 'Pupil Capture',
     'recording_software_version': '1.16.95',
     'recording_uuid': 'e5059604-26f1-42ed-8e35-354198b56021',
     'start_time_synced_s': 2294.807856069,
     'start_time_system_s': 1570725800.220913,
     'system_info': 'User: test_user, Platform: Linux'}

You can also load the user info with:

.. doctest::

    >>> pri.load_user_info(folder) # doctest:+NORMALIZE_WHITESPACE
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
    :ref:`dependencies for data export<export_dependencies>`.

Recorded data can also directly be written to disk:

.. doctest::

    >>> pri.write_netcdf(folder, gaze='recording', output_folder='.')

This will create a ``gaze.nc`` file in the current folder. This file type can
directly be loaded by xarray:

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
