Streaming data
==============

.. currentmodule:: pupil_recording_interface


Video devices
-------------


Video streaming
---------------


Multiple streams
----------------

.. doctest::

    >>> import pupil_recording_interface as pri
    >>> config = pri.VideoStream.Config(
    ...     device_type="uvc",
    ...     device_uid="Pupil Cam1 ID2",
    ...     name="world",
    ...     resolution=(1280, 720),
    ...     fps=60,
    ...     pipeline=[pri.VideoDisplay.Config()],
    ... )
