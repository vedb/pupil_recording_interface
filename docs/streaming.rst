Streaming data
==============

.. currentmodule:: pupil_recording_interface

.. note::

    Make sure that you have installed the necessary
    :ref:`dependencies for streaming<streaming_dependencies>`. If not, you can
    still go through large parts of this guide by streaming from a recording
    included in the package instead of an actual Pupil Core device.


Video devices
-------------

The Pupil Core cameras can be accessed via the :py:class:`VideoDeviceUVC`
class:

.. doctest::

    >>> import pupil_recording_interface as pri
    >>> world_cam = pri.VideoDeviceUVC("Pupil Cam2 ID2", (1280, 720), 60)
    >>> world_cam # doctest:+ELLIPSIS
    <pupil_recording_interface.device.video.VideoDeviceUVC object at ...>

The first argument is the name of the video device (``"Cam1"``, ``"Cam2"`` or
``"Cam3"`` for different generations of the Pupil hardware; ``"ID0"``,
``"ID1"`` and ``"ID2"`` for left and right eye or world camera, respectively).
If you don't have a Pupil Core device or are missing the necessary
dependencies, you can use a dummy device that streams from a recording instead:

.. doctest::

    >>> world_cam = pri.VideoFileDevice(pri.TEST_RECORDING, "world", timestamps="file")

A device needs to be started before streaming any data and stopped afterwards
in order to release the resource. To facilitate this, the :py:class:`Session`
context manager automatically calls the ``start`` and ``stop`` methods of
devices passed to it.

You can grab a video frame and its timestamp from the device with the
:py:meth:`get_frame_and_timestamp` method:

.. doctest::

    >>> with pri.Session(world_cam):
    ...     frame, timestamp = world_cam.get_frame_and_timestamp()
    >>> frame.shape
    (720, 1280, 3)
    >>> timestamp
    1570725800.2383718

Video streams
-------------

The :py:class:`VideoStream` class is a wrapper for video devices that handles
functionality such as polling for new video frames and processing (pupil
detection, recording, ...):

.. doctest::

    >>> stream = pri.VideoStream(world_cam, name="world")
    >>> stream # doctest:+ELLIPSIS
    <pupil_recording_interface.stream.VideoStream object at ...>

The :py:meth:`get_packet` returns a :py:class:`Packet` that bundles the data
retrieved from the device. We use :py:class:`Session` again to handle starting
and stopping of the stream:

.. doctest::

    >>> with pri.Session(stream):
    ...     packet = stream.get_packet()
    >>> packet # doctest:+ELLIPSIS
    pupil_recording_interface.Packet with data:
    * stream_name: world
    * device_uid: world
    * timestamp: 1570725800.2718818
    >>> packet.frame.shape
    (720, 1280, 3)

Multiple streams
----------------

For simultaneous streaming from multiple devices, the :py:class:`StreamManager`
is used. The manager dispatches each stream to a separate process and handles
communication between those processes. Instead of constructing
:py:class:`VideoStream` instances, we use a list of
:py:class:`VideoStream.Config` instances:

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
    ...     pri.VideoStream.Config(
    ...         device_type="uvc",
    ...         device_uid="Pupil Cam2 ID0",
    ...         name="eye0",
    ...         resolution=(192, 192),
    ...         fps=120,
    ...         pipeline=[pri.VideoDisplay.Config()],
    ...     ),
    ...     pri.VideoStream.Config(
    ...         device_type="uvc",
    ...         device_uid="Pupil Cam2 ID1",
    ...         name="eye1",
    ...         resolution=(192, 192),
    ...         fps=120,
    ...         pipeline=[pri.VideoDisplay.Config()],
    ...     ),
    ... ]

The manager then constructs the proper streams and devices from this list.
With ``duration=30``, the manager will stop streaming after 30 seconds.

.. note::

    The concept of pipelines and processes such as :py:class:`VideoDisplay`
    is explained in detail in :ref:`processing`.

.. doctest::

    >>> manager = pri.StreamManager(configs, duration=30)
    >>> manager.streams # doctest:+ELLIPSIS
    {'eye0': <...>, 'eye1': <...>, 'world': <...>}

Alternatively, use this dummy configuration:

.. doctest::

    >>> configs = [
    ...     pri.VideoStream.Config(
    ...         device_type="video_file",
    ...         device_uid="world",
    ...         loop=False,
    ...         pipeline=[pri.VideoDisplay.Config()],
    ...     ),
    ...     pri.VideoStream.Config(
    ...         device_type="video_file",
    ...         device_uid="eye0",
    ...         loop=False,
    ...         pipeline=[pri.VideoDisplay.Config()],
    ...     ),
    ...     pri.VideoStream.Config(
    ...         device_type="video_file",
    ...         device_uid="eye1",
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
    manager.streams["eye0"].pipeline = None
    manager.streams["eye1"].pipeline = None

Now we can run the manager to start streaming and simultaneously print out
the current frame rates for each stream to the command line. You should see
three windows opening with the eye and world video streams.

.. doctest::

    >>> with manager:
    ...     while not manager.stopped:
    ...         if manager.all_streams_running:
    ...             print("\r" + manager.format_status("fps", sleep=0.1), end="") # doctest:+ELLIPSIS,+NORMALIZE_WHITESPACE
    eye0: ..., eye1: ..., world: ...

The manager will automatically stop after the specified duration and can also
be stopped with a keyboard interrupt. When no duration is set, the manager
will run indefinitely.
