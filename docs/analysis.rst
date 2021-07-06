.. _analysis:

Offline analysis
================

.. currentmodule:: pupil_recording_interface

pupil_recording_interface provides straightforward interfaces for post-hoc
pupil detection, calibration and gaze mapping, similar to Pupil Player.


Pupil detection
---------------

.. note::

    Make sure that you have installed the necessary
    :ref:`dependencies for pupil detection<pupil_detection_dependencies>`.

We start by creating a :py:class:`PupilDetector` in the same way as in the
:ref:`processing tutorial<processing>`.

.. doctest::

    >>> import pupil_recording_interface as pri
    >>> pupil_detector = pri.PupilDetector(camera_id=0)

For post-hoc pupil detection we first create a :py:class:`VideoReader` instance
that points to an eye camera video. Now we can use the
:py:meth:`PupilDetector.batch_run` method, which will return a list containing
pupil data for each frame:

.. doctest::

    >>> eye0_reader = pri.VideoReader(
    ...     pri.get_test_recording(), stream="eye0", color_format="gray"
    ... )
    >>> pupil_list_eye0 = pupil_detector.batch_run(eye0_reader)
    >>> pupil_list_eye0[0] # doctest:+NORMALIZE_WHITESPACE +ELLIPSIS
    {'ellipse':
        {'center': (96..., 130...),
         'axes': (39..., 44...),
         'angle': 77...},
     'diameter': 44...,
     'location': (96..., 130...),
     'confidence': 0.99,
     'internal_2d_raw_data': ...,
     'norm_pos': (0.5..., 0.6...),
     'timestamp': 2294...,
     'method': '2d c++',
     'id': 0,
     'topic': 'pupil'}

We can also tell the detector to stop after 100 frames and return a dataset:

.. doctest::

    >>> pupil_detector.batch_run(eye0_reader, end=100, return_type="dataset")
    <xarray.Dataset>
    Dimensions:         (pixel_axis: 2, time: 100)
    Coordinates:
      * time            (time) datetime64[ns] 2019-10-10T16:43:20.280291796 ... 2019-10-10T16:43:21.079125643
      * pixel_axis      (pixel_axis) <U1 'x' 'y'
    Data variables:
        eye             (time) int64 0 0 0 0 0 0 0 0 0 0 0 ... 0 0 0 0 0 0 0 0 0 0 0
        confidence      (time) float64 0.99 0.9674 0.924 ... 0.9381 0.9711 0.9554
        diameter        (time) float64 44.2 44.2 44.37 44.35 ... 45.75 45.8 45.79
        ellipse_angle   (time) float64 77.64 78.05 76.35 77.67 ... 78.78 80.25 79.18
        pupil_norm_pos  (time, pixel_axis) float64 0.5005 0.6779 ... 0.5067 0.677
        ellipse_center  (time, pixel_axis) float64 96.1 130.1 96.13 ... 97.29 130.0
        ellipse_axes    (time, pixel_axis) float64 39.78 44.2 39.68 ... 41.15 45.79

Marker detection
----------------

To detect calibration markers in the world camera images, we can use the
:py:class:`CircleDetector`:

.. doctest::

    >>> marker_detector = pri.CircleDetector()

This process also has a :py:meth:`CircleDetector.batch_run` method, to which
we pass a :py:class:`VideoReader` for the world video:

.. doctest::

    >>> world_reader = pri.VideoReader(pri.get_test_recording())
    >>> marker_list = marker_detector.batch_run(world_reader)
    >>> marker_list[0] # doctest:+NORMALIZE_WHITESPACE +ELLIPSIS
    {'ellipses': [((202..., 258...), (3..., 7...), 5...),
                  ((202..., 258...), (9..., 14...), 7...),
                  ((202..., 258...), (14..., 21...), 8...)],
     'img_pos': (202..., 258...),
     'norm_pos': (0.1..., 0.6...),
     'marker_type': 'Ref',
     'timestamp': 2294...,
     'frame_index': 0}

Again, we can specify a stop (and start) index and return a dataset:

.. doctest::

    >>> marker_detector.batch_run(world_reader, end=100, return_type="dataset")
    <xarray.Dataset>
    Dimensions:      (pixel_axis: 2, time: 34)
    Coordinates:
      * time         (time) datetime64[ns] 2019-10-10T16:43:22.248995781 ... 2019-10-10T16:43:23.472124815
      * pixel_axis   (pixel_axis) <U1 'x' 'y'
    Data variables:
        frame_index  (time) int64 66 67 68 69 70 71 72 73 ... 93 94 95 96 97 98 99
        location     (time, pixel_axis) float64 619.1 352.2 618.9 ... 615.7 354.0

Calibration
-----------

After detecting pupils and calibration markers, we can now run a calibration
with a :py:class:`Calibration` instance:

.. doctest::

    >>> calibration = pri.Calibration(resolution=(1280, 720))

We pass the detected pupils and calibration markers to
:py:meth:`Calibration.batch_run` to obtain a monocular calibration.

.. doctest::

    >>> calibration.batch_run(pupil_list_eye0, marker_list) # doctest:+NORMALIZE_WHITESPACE +ELLIPSIS
    {'params': ([-28..., -29..., 15..., 14..., 41..., -29..., 13...],
                [-2..., -14..., 2..., 13..., -0..., 0..., 4...],
                7)}

It is also possible to perform a binocular calibration, provided that we have
detected pupils from the second eye camera. However, we need to take care that
the detected pupils are in the correct chronological order. We can use
:py:meth:`merge_pupils` for this:

.. doctest::

    >>> eye1_reader = pri.VideoReader(
    ...     pri.get_test_recording(), stream="eye1", color_format="gray"
    ... )
    >>> pupil_detector.camera_id = 1
    >>> pupil_list_eye1 = pupil_detector.batch_run(eye1_reader)
    >>> pupil_list = pri.merge_pupils(pupil_list_eye0, pupil_list_eye1)

Now we can run a binocular calibration. As you can see, the result is different
this time, as it includes binocular calibration coefficients as well as
monocular coefficients for each eye:

.. doctest::

    >>> calibration_result = calibration.batch_run(pupil_list, marker_list)
    >>> calibration_result # doctest:+NORMALIZE_WHITESPACE +ELLIPSIS
    {'params': ([-1..., -12..., -2..., 1..., -0..., 8..., 5..., -2..., 1...,
                 -6..., 1..., 5..., 5...],
                [8..., 16..., 4..., 7..., -4..., -12..., -13..., 13..., -3...,
                 -8..., -10..., 17..., -6...], 13),
     'params_eye0': ([-28..., -29..., 15..., 14..., 41..., -29..., 13...],
                     [2..., 14..., -2..., -13..., 0..., -0..., -3...], 7),
     'params_eye1': ([-3..., -0..., 2..., -1..., 3..., -0..., 1...],
                     [1..., -2..., -1..., 9..., -1..., 6..., 0...], 7)}

.. note::

    Running a calibration on pupil and marker datasets is not yet possible.


Gaze mapping
------------

Finally, we can use the :py:class:`GazeMapper` to map detected pupils to gaze
data according to a previously obtained calibration:

.. doctest::

    >>> gaze_mapper = pri.GazeMapper(calibration=calibration_result)

As usual, we use the :py:meth:`GazeMapper.batch_run` method for post-hoc
mapping:

.. doctest::

    >>> gaze_list = gaze_mapper.batch_run(pupil_list)
    >>> gaze_list[0] # doctest:+NORMALIZE_WHITESPACE +ELLIPSIS
    {'topic': 'gaze.2d.01.',
      'norm_pos': (0.33..., 0.67...),
      'confidence': 0.97...,
      'timestamp': 2294...,
      'base_data': [...]}

The method can also return a dataset, although we need to provide a dictionary
with the recording info to get the correspondence between recorded (monotonic)
timestamps and datetime timestamps:

.. doctest::

    >>> info = pri.load_info(pri.get_test_recording())
    >>> gaze_mapper.batch_run(pupil_list, return_type="dataset", info=info)
    <xarray.Dataset>
    Dimensions:             (pixel_axis: 2, time: 5154)
    Coordinates:
      * time                (time) datetime64[ns] 2019-10-10T16:43:20.278882504 ... 2019-10-10T16:43:41.326934099
      * pixel_axis          (pixel_axis) <U1 'x' 'y'
    Data variables:
        eye                 (time) int64 2 2 2 2 2 2 2 2 2 2 ... 2 2 2 2 2 2 2 2 2 2
        gaze_norm_pos       (time, pixel_axis) float64 0.3359 0.6786 ... 0.9603
        gaze_confidence_2d  (time) float64 0.9761 0.9586 0.9473 ... 1.0 0.984 0.984

.. note::

    Running gaze mapping on a pupil dataset is not yet possible.
