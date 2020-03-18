""""""


class StreamConfig(object):
    """ Configuration for streams. """

    def __init__(self, device_type, device_uid, name=None, **kwargs):
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
        self.name = name or self.device_uid

        for k, v in kwargs.items():
            setattr(self, k, v)


class VideoConfig(StreamConfig):
    """ Configuration for video streams. """

    def __init__(self, device_type, device_uid, name=None,
                 resolution = None, fps = 30, color_format='bgr24', side='both', **kwargs):
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
        super(VideoConfig, self).__init__(
            device_type, device_uid, name, **kwargs)

        self.fps = fps
        self.resolution = resolution
        self.color_format = color_format
        self.side = side


class OdometryConfig(StreamConfig):
    """ Configuration for odometry streams. """
    # TODO rename to MotionConfig
