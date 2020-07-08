.. _processing:

Processing and recording data
=============================

.. currentmodule:: pupil_recording_interface


Pupil detection
---------------

.. note::

    Make sure that you have installed the necessary
    :ref:`dependencies for pupil_detection<pupil_detection_dependencies>`.

.. doctest::

    >>> import pupil_recording_interface as pri
    >>> eye0_video = pri.VideoFileDevice(pri.TEST_RECORDING, "eye0")
    >>> stream = pri.VideoStream(eye0_video, color_format="gray")
    >>> detector = pri.PupilDetector()

.. doctest::

    >>> with pri.Session(stream, detector):
    ...     packet = stream.get_packet()
    ...     packet = detector.process_packet(packet)
    ...     packet.pupil # doctest:+NORMALIZE_WHITESPACE +ELLIPSIS
    {'ellipse':
        {'center': (96..., 130...),
         'axes': (39..., 44...),
         'angle': 77...},
     'diameter': 44...,
     'location': (96..., 130...),
     'confidence': 0.99,
     'norm_pos': (0.5..., 0.6...),
     'timestamp': 1570725800...,
     'method': '2d c++',
     'id': None,
     'topic': 'pupil'}

.. note::

    So far, only the standard 2D pupil detector is available. We are working
    on supporting more pupil detection methods.


Pipelines
---------

.. doctest::

    >>> configs = [
    ...     pri.VideoStream.Config(
    ...         device_type="video_file",
    ...         device_uid="eye0",
    ...         loop=False,
    ...         pipeline=[
    ...             pri.PupilDetector.Config(),
    ...             pri.VideoDisplay.Config(overlay_pupil=True),
    ...         ],
    ...     ),
    ... ]
    >>> manager = pri.StreamManager(
    ...     configs, duration=10, folder=pri.TEST_RECORDING, policy="read"
    ... )

.. testcode::
    :hide:

    manager.streams["eye0"].pipeline = None

.. doctest::

    >>> manager.run()

Calibration
-----------

.. note::

    So far, only the standard 2D calibration is available. We are working
    on supporting more calibration methods.


Gaze mapping
------------

.. note::

    So far, only the standard 2D gaze mapping is available. We are working
    on supporting more gaze mapping methods.

Recording
---------

.. note::

    Make sure that you have installed the necessary
    :ref:`dependencies for recording<recording_dependencies>`.
