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
    ...     packet.pupil # doctest:+NORMALIZE_WHITESPACE
    {'ellipse':
        {'center': (96.12611389160156, 130.08692932128906),
         'axes': (39.72499465942383, 44.183467864990234),
         'angle': 77.9285202026367},
     'diameter': 44.183467864990234,
     'location': (96.12611389160156, 130.08692932128906),
     'confidence': 0.99,
     'norm_pos': (0.5006568431854248, 0.6775360902150472),
     'timestamp': 1570725800.2802918,
     'method': '2d c++',
     'id': None,
     'topic': 'pupil'}

.. note::

    So far, only the standard 2D pupil detector is available. We are working
    on supporting more pupil detection methods.

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
