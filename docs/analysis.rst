.. _analysis:

Offline analysis
================

.. currentmodule:: pupil_recording_interface

We plan to provide straightforward interfaces for post-hoc pupil detection,
calibration and gaze mapping, similar to Pupil Player.


Pupil detection
---------------

.. doctest::

    >>> import pupil_recording_interface as pri
    >>> detector = pri.PupilDetector(camera_id=0)

.. doctest::

    >>> reader = pri.VideoReader(
    ...     pri.get_test_recording(), stream="eye0", color_format="gray"
    ... )
    >>> pupil_list = detector.batch_run(reader, end=100)
    >>> pupil_list[0] # doctest:+NORMALIZE_WHITESPACE +ELLIPSIS
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

.. doctest::

    >>> detector.batch_run(reader, end=100, return_type="dataset")
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

.. note::

    This part of the package is still in development.


Calibration
-----------

.. note::

    This part of the package is still in development.


Gaze mapping
------------

.. note::

    This part of the package is still in development.
