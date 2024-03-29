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

    >>> world_cam = pri.VideoFileDevice(pri.get_test_recording(), "world", timestamps="file")

A device needs to be started before streaming any data and stopped afterwards
in order to release the resource. To facilitate this, using the device as a
context manager automatically calls its ``start`` and ``stop`` methods upon
entering and exiting, respectively.

You can grab a video frame and its timestamp from the device with the
:py:meth:`get_frame_and_timestamp` method:

.. doctest::

    >>> with world_cam:
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
retrieved from the device. We use a context manager again to handle starting
and stopping of the stream:

.. doctest::

    >>> with stream:
    ...     packet = stream.get_packet()
    >>> packet # doctest:+ELLIPSIS
    pupil_recording_interface.Packet with data:
    * stream_name: world
    * device_uid: world
    * timestamp: 1570725800.2383718
    >>> packet.frame.shape
    (720, 1280, 3)

Multiple streams
----------------

For simultaneous streaming from multiple devices, the :py:class:`StreamManager`
is used. The manager dispatches each stream to a separate process and handles
communication between those processes. Instead of constructing
:py:class:`VideoStream` instances, we use a list of
:py:meth:`VideoStream.Config` instances:

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
    is explained in detail in :ref:`processing` and the config mechanism
    in :ref:`custom`.

.. doctest::

    >>> manager = pri.StreamManager(configs, duration=30)
    >>> manager.streams # doctest:+ELLIPSIS
    {'world': <...>, 'eye0': <...>, 'eye1': <...>}

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
    ...     configs, duration=10, folder=pri.get_test_recording(), policy="read"
    ... )

.. testcode::
    :hide:

    manager.streams["world"].pipeline = None
    manager.streams["eye0"].pipeline = None
    manager.streams["eye1"].pipeline = None

Now we can run the manager to start streaming. You should see three windows
opening with the eye and world video streams.

.. doctest::

    >>> manager.run()

The manager will automatically stop after the specified duration and can also
be stopped with a keyboard interrupt. When no duration is set, the manager
will run indefinitely.

It is also possible to run the manager in a non-blocking fashion
by using it as a context manager. This allows us for example to print the
current frame rates for each stream to the command line:

.. doctest::

    >>> with manager:
    ...     while not manager.stopped:
    ...         if manager.all_streams_running:
    ...             print("\r" + manager.format_status("fps", sleep=0.1), end="") # doctest:+ELLIPSIS,+NORMALIZE_WHITESPACE
    eye0: ..., eye1: ..., world: ...

Self-contained scripts and Jupyter notebooks for streaming that you can
download and modify can be found in the
:ref:`online examples section<online_examples>`.


UVC camera settings
-------------------

The Pupil Core cameras implement the USB Video Class (UVC) protocol and Pupil
Labs provides a Python wrapper for accessing the cameras called ``pyuvc``.
In turn, pupil_recording_interface provides a high-level interface to this via
the :py:class:`VideoDeviceUVC` class.

Possible combinations of resolutions and FPS can be queried via the
``available_modes`` attribute, returning a list of
``(horizontal_res, vertical_res, fps)`` tuples:

.. doctest::

    >>> from pprint import pprint
    >>> pprint(world_cam.available_modes) # doctest:+SKIP
    [(1920, 1080, 30),
     (640, 480, 120),
     (640, 480, 90),
     (640, 480, 60),
     (640, 480, 30),
     (1280, 720, 60),
     (1280, 720, 30),
     (1024, 768, 30),
     (800, 600, 60),
     (1280, 1024, 30),
     (320, 240, 120)]

Other settings (called controls) together with valid ranges of values can be
obtained via ``available_controls``.

.. doctest::

    >>> pprint(world_cam.available_controls) # doctest:+SKIP
    {'Absolute Exposure Time': range(1, 500),
     'Auto Exposure Mode': {'aperture priority mode': 8,
                            'auto mode': 2,
                            'manual mode': 1,
                            'shutter priority mode': 4},
     'Auto Exposure Priority': (0, 1),
     'Backlight Compensation': range(0, 2),
     'Brightness': range(-64, 64),
     'Contrast': range(0, 64),
     'Gain': range(0, 100),
     'Gamma': range(72, 500),
     'Hue': range(-40, 40),
     'Power Line frequency': {'50Hz': 1, '60Hz': 2, 'Disabled': 0},
     'Saturation': range(0, 128),
     'Sharpness': range(0, 6),
     'White Balance temperature': range(2800, 6500),
     'White Balance temperature,Auto': (0, 1)}

The current settings of a running device are stored in the ``controls``
attribute.

.. doctest::

    >>> with world_cam: # doctest:+SKIP
    ...     pprint(world_cam.controls)
    {'Absolute Exposure Time': 32,
     'Auto Exposure Mode': 8,
     'Auto Exposure Priority': 1,
     'Backlight Compensation': 1,
     'Brightness': 0,
     'Contrast': 32,
     'Gain': 0,
     'Gamma': 100,
     'Hue': 0,
     'Power Line frequency': 1,
     'Saturation': 60,
     'Sharpness': 2,
     'White Balance temperature': 4600,
     'White Balance temperature,Auto': 1}

You can also assign controls by passing a dictionary as the ``controls``
constructor argument...

.. doctest::

    >>> world_cam = pri.VideoDeviceUVC(
    ...     "Pupil Cam2 ID2", (1280, 720), 30, controls={"Gamma": 200}
    ... )
    ... with world_cam: # doctest:+SKIP
    ...     print(world_cam.controls["Gamma"])
    200

...or to a running device in the same manner:

.. doctest::

    >>> with world_cam: # doctest:+SKIP
    ...     world_cam.controls = {"Gamma": 120}
    ...     print(world_cam.controls["Gamma"])
    120
