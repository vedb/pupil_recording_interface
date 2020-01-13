""""""
import abc

import cv2
# TODO import uvc here


class BaseVideoDevice(object):
    """ Base class for all video devices. """

    def __init__(self, device_name, resolution, fps, aliases=None,
                 init_capture=True):
        """ Constructor.

        Parameters
        ----------
        device_name: str
            The name of the video device. For UVC devices, this corresponds
            to the ``'name'`` field of the items obtained through
            ``uvc.get_device_list()``. Can also be a key of `aliases`.

        resolution: tuple, len 2
            Desired horizontal and vertical camera resolution.

        fps: int
            Desired camera refresh rate.

        aliases: dict, optional
            A mapping from aliases to valid device names. See `device_name`.

        init_capture: bool, default True
            If True, initialize the underlying capture upon construction.
            Set to False for multi-threaded recording.
        """
        # Replace name with alias, if applicable
        device_name = (aliases or {}).get(device_name, device_name)

        self.device_name = device_name
        self.resolution = resolution
        self.fps = fps

        if init_capture:
            self.capture = self._get_capture(device_name, resolution, fps)
        else:
            self.capture = None

    @classmethod
    @abc.abstractmethod
    def _get_capture(cls, device_name, resolution, fps):
        """ Get a capture instance for a device by name. """

    @abc.abstractmethod
    def _get_frame_and_timestamp(self, mode='img'):
        """ Get a frame and its associated timestamp. """

    def show_frame(self, frame):
        """ Show a frame via OpenCV.

        Parameters
        ----------
        frame : array_like
            The frame to display.
        """
        cv2.imshow(self.device_name, frame)
        return cv2.waitKey(1)


class VideoDeviceUVC(BaseVideoDevice):
    """ UVC video device. """

    @classmethod
    def _get_connected_device_uids(cls):
        """ Get a mapping from devices names to UIDs. """
        import uvc
        return {
            device['name']: device['uid'] for device in uvc.device_list()}

    @classmethod
    def _get_device_uid(cls, device_name):
        """ Get the UID for a device by name. """
        try:
            return cls._get_connected_device_uids()[device_name]
        except KeyError:
            raise ValueError(
                'Device with name {} not connected.'.format(device_name))

    @classmethod
    def _get_available_modes(cls, device_uid):
        """ Get the available modes for a device by UID. """
        import uvc
        return uvc.Capture(device_uid).avaible_modes  # [sic]

    @classmethod
    def _get_controls(cls, device_uid):
        """ Get the current controls for a device by UID. """
        import uvc
        return {
            c.display_name: c.value for c in uvc.Capture(device_uid).controls}

    @classmethod
    def _get_capture(cls, device_name, resolution, fps):
        """ Get a capture instance for a device by name. """
        device_uid = cls._get_device_uid(device_name)

        # verify selected mode
        if resolution + (fps,) not in cls._get_available_modes(device_uid):
            raise ValueError('Unsupported frame mode: {}x{}@{}fps.'.format(
                resolution[0], resolution[1], fps))

        import uvc
        capture = uvc.Capture(device_uid)
        capture.frame_mode = resolution + (fps,)

        return capture

    @classmethod
    def _get_timestamp(cls):
        """ Get the current monotonic time from the UVC backend. """
        import uvc
        return uvc.get_time_monotonic()

    def _get_frame_and_timestamp(self, mode='img'):
        """ Get a frame and its associated timestamp. """
        if mode not in ('img', 'bgr', 'gray', 'jpeg_buffer'):
            raise ValueError('Unsupported mode: {}'.format(mode))

        uvc_frame = self.capture.get_frame()

        return getattr(uvc_frame, mode), uvc_frame.timestamp

    @property
    def device_uid(self):
        """ The UID of this device. """
        return self._get_device_uid(self.device_name)

    @property
    def available_modes(self):
        """ Available frame modes for this device. """
        if self.capture is None:
            return self._get_available_modes(self.device_uid)
        else:
            return self.capture.avaible_modes  # [sic]

    @property
    def controls(self):
        """ Current controls for this device. """
        if self.capture is None:
            return self._get_controls(self.device_uid)
        else:
            return {c.display_name: c.value for c in self.capture.controls}

    def get_uvc_frame(self):
        """ Grab a uvc.Frame from the device.

        Returns
        -------
        uvc.Frame:
            The captured frame.
        """
        return self.capture.get_frame()


class VideoDeviceFLIR(BaseVideoDevice):

    @classmethod
    def _get_capture(cls, device_name, resolution, fps):
        """ Get a capture instance for a device by name. """
        # TODO return capture
        raise NotImplementedError('Not yet implemented.')

    def _get_frame_and_timestamp(self, mode='img'):
        """ Get a frame and its associated timestamp. """
        # TODO return frame and timestamp from self.capture
        # TODO return grayscale frame if mode=='gray'
        raise NotImplementedError('Not yet implemented.')
