""""""


class BaseConfig(object):
    """ Base class for all configurations. """

    def __init__(self, **kwargs):
        """ Constructor. """
        # TODO Replace with self.kwargs = kwargs?
        for k, v in kwargs.items():
            setattr(self, k, v)


class StreamConfig(BaseConfig):
    """ Configuration for streams. """

    stream_type: str

    def __init__(
        self, device_type, device_uid, pipeline=None, name=None, **kwargs
    ):
        """ Constructor.

        Parameters
        ----------
        device_type: str
            The type of device where the stream comes from.

        device_uid: str
            The UID of the device.

        name: str, optional
            The name of the stream. If not specified, `device_uid` will be
            used.
        """
        self.device_type = device_type
        self.device_uid = device_uid
        self.pipeline = pipeline
        self.name = name or self.device_uid

        super().__init__(**kwargs)


class VideoConfig(StreamConfig):
    """ Configuration for video streams. """

    stream_type = "video"

    def __init__(
        self,
        device_type,
        device_uid,
        resolution,
        fps,
        pipeline=None,
        name=None,
        color_format="bgr24",
        side="both",
        **kwargs,
    ):
        """ Constructor.

        Parameters
        ----------
        device_type: str
            The type of device where the stream comes from.

        device_uid: str
            The UID of the device.

        resolution: tuple, len 2
            Desired horizontal and vertical camera resolution.

        fps: int
            Desired camera refresh rate.

        name: str, optional
            The name of the stream. If not specified, `device_uid` will be
            used.

        color_format: str, default 'bgr24'
            The target color format. Set to 'gray' for eye cameras.

        side: str, default 'both'
            For stereo cameras, which side to record. Can be 'left', 'right'
            or 'both'.
        """
        super().__init__(
            device_type, device_uid, pipeline=pipeline, name=name, **kwargs
        )

        self.fps = fps
        self.resolution = resolution
        self.color_format = color_format
        self.side = side


class OdometryConfig(StreamConfig):
    """ Configuration for odometry streams. """

    stream_type = "odometry"

    # TODO rename to MotionConfig


class ProcessConfig(BaseConfig):
    """ Configuration for processes. """

    process_type: str

    def __init__(self, block=True, **kwargs):
        """ Constructor. """
        self.block = block

        super().__init__(**kwargs)


class VideoDisplayConfig(ProcessConfig):
    """ Configuration for video displays. """

    process_type = "video_display"

    def __init__(self, overlay_pupil=False, **kwargs):
        """ Constructor. """
        self.overlay_pupil = overlay_pupil

        super().__init__(**kwargs)


class VideoRecorderConfig(ProcessConfig):
    """ Configuration for video recorders. """

    process_type = "video_recorder"

    def __init__(
        self,
        folder=None,
        resolution=None,
        fps=None,
        color_format=None,
        codec="libx264",
        **kwargs,
    ):
        """ Constructor. """
        self.folder = folder
        self.resolution = resolution
        self.fps = fps
        self.color_format = color_format
        self.codec = codec

        super().__init__(**kwargs)


class OdometryRecorderConfig(ProcessConfig):
    """ Configuration for odometry recorders. """

    process_type = "odometry_recorder"

    def __init__(self, folder=None, **kwargs):
        """ Constructor. """
        self.folder = folder

        super().__init__(**kwargs)


class PupilDetectorConfig(ProcessConfig):
    """ Configuration for pupil detectors. """

    process_type = "pupil_detector"
