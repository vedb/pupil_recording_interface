Streaming data
==============

.. currentmodule:: pupil_recording_interface


Video devices
-------------

.. doctest::

    >>> import pupil_recording_interface as pri
    >>> world_cam = pri.VideoDeviceUVC("Pupil Cam2 ID2", (1280, 720), 60)
    >>> world_cam.start() # doctest:+SKIP

.. doctest::

    >>> frame, timestamp = world_cam.get_frame_and_timestamp() # doctest:+SKIP

Video streaming
---------------

.. doctest::

    >>> stream = pri.VideoStream(world_cam, name="world")
    >>> stream.start() # doctest:+SKIP

.. doctest::

    >>> packet = stream.get_packet() # doctest:+SKIP


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

    >>> manager.start() # doctest:+SKIP
    >>> manager.spin() # doctest:+SKIP
    >>> manager.stop() # doctest:+SKIP

.. doctest::

    >>> with manager: # doctest:+SKIP
    ...     while not manager.stopped:
    ...         if manager.all_streams_running:
    ...             print("\r" + manager.format_status("fps"), end="")
