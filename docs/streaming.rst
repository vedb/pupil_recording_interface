Streaming data
==============

.. currentmodule:: pupil_recording_interface

.. note::

    Make sure that you have installed the necessary
    :ref:`dependencies for streaming<streaming_dependencies>`. If not, you can
    still go through large parts of this tutorial by streaming from a recording
    included in the package instead of an actual Pupil Core device.


Video devices
-------------

.. doctest::

    >>> import pupil_recording_interface as pri
    >>> world_cam = pri.VideoDeviceUVC("Pupil Cam2 ID2", (1280, 720), 60)

.. doctest::

    >>> world_cam = pri.VideoFileDevice(pri.TEST_RECORDING, "world", timestamps="file")

.. doctest::

    >>> with pri.Session(world_cam):
    ...     frame, timestamp = world_cam.get_frame_and_timestamp()
    >>> frame.shape
    (720, 1280, 3)
    >>> timestamp
    1570725800.2383718

Video streaming
---------------

.. doctest::

    >>> stream = pri.VideoStream(world_cam, name="world")

.. doctest::

    >>> with pri.Session(stream):
    ...     packet = stream.get_packet()
    >>> packet # doctest:+ELLIPSIS
    pupil_recording_interface.Packet with data:
    * stream_name: world
    * device_uid: world
    * timestamp: 1570725800.2718818


Multiple streams
----------------

.. doctest::

    >>> configs = [
    ...     pri.VideoStream.Config(
    ...         device_type="uvc",
    ...         device_uid="Pupil Cam2 ID2",
    ...         name="world",
    ...         resolution=(1280, 720),
    ...         fps=60,
    ...         pipeline=[pri.VideoDisplay.Config()],
    ...     ),
    ... ]

.. doctest::

    >>> manager = pri.StreamManager(configs, duration=30)
    >>> manager.streams # doctest:+ELLIPSIS
    {'world': <...>}

.. doctest::

    >>> configs = [
    ...     pri.VideoStream.Config(
    ...         device_type="video_file",
    ...         device_uid="world",
    ...         name="world",
    ...         resolution=(1280, 720),
    ...         fps=60,
    ...         loop=False,
    ...         pipeline=[pri.VideoDisplay.Config()],
    ...     ),
    ... ]
    >>> manager = pri.StreamManager(
    ...     configs, duration=10, folder=pri.TEST_RECORDING, policy="read"
    ... )

.. testcode::
    :hide:

    manager.streams["world"].pipeline = None

.. doctest::

    >>> with manager:
    ...     while not manager.stopped:
    ...         if manager.all_streams_running:
    ...             print("\r" + manager.format_status("fps", sleep=0.1), end="") # doctest:+ELLIPSIS,+NORMALIZE_WHITESPACE
    world: ...
