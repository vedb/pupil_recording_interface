.. _processing:

Processing and recording data
=============================

.. currentmodule:: pupil_recording_interface

pupil_recording_interface uses the concept of *processes* to handle data
produced by devices and streams. This tutorial will present the pupil
detector as an example process, then introduce the concept of pipelines and
notifications and finally list other available processes such as the gaze
mapper and recorders.


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
    >>> eye0_stream = pri.VideoStream(eye0_video, color_format="gray")
    >>> detector = pri.PupilDetector()

Each process has a ``process_packet`` method that takes a :py:class:`Packet`
produced by the stream as an input and returns the same packet, possibly
attaching additional attributes. Note that the detector also needs to be
started and stopped via the :py:class:`Session` context manager:

.. doctest::

    >>> with pri.Session(eye0_stream, detector):
    ...     packet = eye0_stream.get_packet()
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

Multiple processes can be chained with a :py:class:`Pipeline`, e.g. a pupil
detector and a display that shows the eye camera image with an overlay of the
detected pupil:

.. doctest::

    >>> pipeline = pri.Pipeline(
    ...     [pri.PupilDetector(), pri.VideoDisplay("eye")]
    ... )
    >>> pipeline.steps # doctest:+ELLIPSIS +NORMALIZE_WHITESPACE
    [<pupil_recording_interface.process.pupil_detector.PupilDetector ...>,
     <pupil_recording_interface.process.display.VideoDisplay ...>]


.. testcode::
    :hide:

    pipeline.steps.pop()


Starting/stopping the pipeline also starts/stop all of its processes. The
``process`` method pipes a packet through all of the steps:

.. doctest::

    >>> with pri.Session(eye0_stream, pipeline):
    ...     pipeline.process(eye0_stream.get_packet())
    ...     input("Press enter to close") # doctest:+SKIP

.. note::

    The ``input()`` call is necessary here because the pipeline is stopped upon
    exiting the context manager, which includes closing the window of the video
    display.


Pipelines can easily be attached to streams created with the config mechanism
for use with a stream manager:

.. doctest::

    >>> configs = [
    ...     pri.VideoStream.Config(
    ...         device_type="video_file",
    ...         device_uid="eye0",
    ...         loop=False,
    ...         pipeline=[
    ...             pri.PupilDetector.Config(),
    ...             pri.VideoDisplay.Config(),
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


Notifications
-------------

In addition to packets which are emitted every time a stream provides new
data (e.g. a new video frame from a camera), processes also need to deal with
asynchronous data from other sources.

This data falls into two categories:

1. Events emitted from the :py:class:`StreamManager`, e.g. instructing the
   :py:class:`Calibration` process to start collecting calibration data.
2. Data from other processes, e.g. information about detected pupils from an
   eye camera stream that the :py:class:`GazeMapper` process - attached to the
   world camera stream - uses to calculate the current gaze position in the
   world video frame.

For this purpose, processes have a ``process_notifications`` method that
handles this kind of data. Notifications are passed a list of dictionaries; the
dictionary key denotes the type of notification and the value contains the
notification's payload. Internally, each process filters the notification list
and responds only to certain pre-defined types.

One class of notifications that all processes understand are ``"pause_process"``
and ``"resume_process"`` that will temporarily pause the process:

.. doctest::

    >>> detector.paused
    False
    >>> detector.process_notifications([{"pause_process": "PupilDetector"}])
    >>> detector.paused
    True
    >>> detector.process_notifications([{"resume_process": "PupilDetector"}])
    >>> detector.paused
    False

Note that the notification's payload must match ``detector.process_name`` in
order for this to work.


Gaze mapping
------------

The :py:class:`GazeMapper` collects data from one or two
:py:class:`PupilDetector` s and maps them to a gaze position according to a
previously defined calibration.

.. doctest::

    >>> detector = pri.PupilDetector(camera_id=0)
    >>> mapper = pri.GazeMapper()

.. doctest::

    >>> with pri.Session(eye0_stream, detector, mapper):
    ...     for _ in range(11):
    ...         packet = detector.process_packet(eye0_stream.get_packet())
    ...         mapper.process_notifications([{"eye0": {"pupil": packet.pupil}}])
    ...     mapper.get_mapped_gaze() # doctest:+NORMALIZE_WHITESPACE +ELLIPSIS
    [{'topic': 'gaze.2d.0.',
      'norm_pos': (1.40..., -1.08...),
      'confidence': 0.99...,
      'timestamp': 1570725800.2802918,
      'base_data': [...]}]



.. doctest::

    >>> configs = [
    ...     pri.VideoStream.Config(
    ...         device_type="video_file",
    ...         device_uid="world",
    ...         loop=False,
    ...         pipeline=[pri.GazeMapper.Config(), pri.VideoDisplay.Config()],
    ...     ),
    ...     pri.VideoStream.Config(
    ...         device_type="video_file",
    ...         device_uid="eye0",
    ...         loop=False,
    ...         pipeline=[pri.PupilDetector.Config(), pri.VideoDisplay.Config()],
    ...     ),
    ...     pri.VideoStream.Config(
    ...         device_type="video_file",
    ...         device_uid="eye1",
    ...         loop=False,
    ...         pipeline=[pri.PupilDetector.Config(), pri.VideoDisplay.Config()],
    ...     ),
    ... ]
    >>> manager = pri.StreamManager(
    ...     configs, duration=10, folder=pri.TEST_RECORDING, policy="read"
    ... )

.. testcode::
    :hide:

    manager.streams["world"].pipeline.steps.pop()
    manager.streams["eye0"].pipeline.steps.pop()
    manager.streams["eye1"].pipeline.steps.pop()


.. note::

    So far, only the standard 2D gaze mapping is available. We are working
    on supporting more gaze mapping methods.


Calibration
-----------

.. note::

    So far, only the standard 2D calibration is available. We are working
    on supporting more calibration methods.

Recording
---------

.. note::

    Make sure that you have installed the necessary
    :ref:`dependencies for recording<recording_dependencies>`.
