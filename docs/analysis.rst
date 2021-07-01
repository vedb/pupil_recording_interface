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
    >>> detector = pri.PupilDetector()

.. doctest::

    >>> reader = pri.VideoReader(
    ...     pri.get_test_recording(), stream="eye0", color_format="gray"
    ... )
    >>> pupil_list = detector.batch_run(reader)
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
     'id': None,
     'topic': 'pupil'}


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
