.. _processing:

Processing and recording data
=============================

.. currentmodule:: pupil_recording_interface

pupil_recording_interface uses the concept of *processes* to handle data
produced by devices and streams. This tutorial will present the pupil
detector as an example process, then introduce the concept of pipelines and
finally list other available processes such as the gaze mapper and recorders.


Pupil detection
---------------

.. note::

    Make sure that you have installed the necessary
    :ref:`dependencies for pupil detection<pupil_detection_dependencies>`.

Pupil detection is implemented in the :py:class:`PupilDetector` class. We
create a stream from an eye video and a detector:

.. doctest::

    >>> import pupil_recording_interface as pri
    >>> eye0_video = pri.VideoFileDevice(pri.TEST_RECORDING, "eye0")
    >>> stream = pri.VideoStream(eye0_video, color_format="gray")
    >>> detector = pri.PupilDetector()

Each process has a ``process_packet`` method that takes a :py:class:`Packet`
produced by the stream as an input and returns the same packet, possibly
attaching additional attributes. Note that the detector also needs to be
started and stopped via the :py:class:`Session` context manager:

.. doctest::

    >>> with pri.Session(stream, detector):
    ...     packet = stream.get_packet()
    ...     packet = detector.process_packet(packet)
    >>> packet.pupil # doctest:+NORMALIZE_WHITESPACE +ELLIPSIS
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

As you can see, the detector has detected a pupil and added the ``pupil``
attribute to the packet containing the location of the pupil among others.

.. note::

    So far, only the standard 2D pupil detector is available. We are working
    on supporting more pupil detection methods.


Pipelines
---------

.. doctest::

    >>> pipeline = pri.Pipeline(
    ...     [pri.PupilDetector(), pri.VideoDisplay("eye", overlay_pupil=True)]
    ... )
    >>> pipeline.steps # doctest:+ELLIPSIS +NORMALIZE_WHITESPACE
    [<pupil_recording_interface.process.pupil_detector.PupilDetector ...>,
     <pupil_recording_interface.process.display.VideoDisplay ...>]


.. testcode::
    :hide:

    pipeline.steps.pop()

.. doctest::

    >>> with pri.Session(stream, pipeline):
    ...     pipeline.process(stream.get_packet())
    ...     input("Press enter to close") # doctest:+SKIP

The ``input()`` call is necessary here because the pipeline is stopped upon
exiting the context manager, which includes closing the window of the video
display.

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

    manager.streams["eye0"].pipeline.steps.pop()

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
