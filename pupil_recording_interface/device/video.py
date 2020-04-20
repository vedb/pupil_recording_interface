""""""
import abc
import time
import logging
from time import monotonic, sleep

import cv2

from pupil_recording_interface.decorators import device
from pupil_recording_interface.device import BaseDevice
from pupil_recording_interface.reader.video import VideoReader
from pupil_recording_interface.errors import DeviceNotConnected

logger = logging.getLogger(__name__)


class BaseVideoDevice(BaseDevice):
    """ Base class for all video devices. """

    def __init__(self, device_uid, resolution, fps, **kwargs):
        """ Constructor.

        Parameters
        ----------
        device_uid: str
            The unique identity of this device. Depending on the device this
            will be a serial number or similar.

        resolution: tuple, len 2
            Desired horizontal and vertical camera resolution.

        fps: int
            Desired camera refresh rate.

        start: bool, default True
            If True, initialize the underlying capture upon construction.
            Set to False for multi-threaded recording.
        """
        super(BaseVideoDevice, self).__init__(device_uid)

        self.resolution = resolution
        self.fps = fps

        self.capture = None
        self.capture_kwargs = kwargs

    @property
    def is_started(self):
        return self.capture is not None

    @classmethod
    @abc.abstractmethod
    def _get_capture(cls, device_uid, resolution, fps, **kwargs):
        """ Get a capture instance for a device by name. """

    @abc.abstractmethod
    def _get_frame_and_timestamp(self, mode="img"):
        """ Get a frame and its associated timestamp. """

    def start(self):
        """ Start this device. """
        if not self.is_started:
            self.capture = self._get_capture(
                self.device_uid,
                self.resolution,
                self.fps,
                **self.capture_kwargs,
            )

    def stop(self):
        """ Stop this device. """
        self.capture = None


@device("uvc")
class VideoDeviceUVC(BaseVideoDevice):
    """ UVC video device. """

    @classmethod
    def _get_connected_device_uids(cls):
        """ Get a mapping from devices names to UIDs. """
        import uvc

        return {device["name"]: device["uid"] for device in uvc.device_list()}

    @classmethod
    def _get_uvc_device_uid(cls, device_name):
        """ Get the UID for a UVC device by name. """
        try:
            return cls._get_connected_device_uids()[device_name]
        except KeyError:
            raise DeviceNotConnected(
                f"Device with name {device_name} not connected."
            )

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
            c.display_name: c.value for c in uvc.Capture(device_uid).controls
        }

    @classmethod
    def _get_capture(cls, uid, resolution, fps, **kwargs):
        """ Get a capture instance for a device by name. """
        import uvc

        device_uid = cls._get_uvc_device_uid(uid)

        # verify selected mode
        if resolution + (fps,) not in cls._get_available_modes(device_uid):
            raise ValueError(
                f"Unsupported frame mode: "
                f"{resolution[0]}x{resolution[1]}@{fps}fps."
            )

        capture = uvc.Capture(device_uid)
        capture.frame_mode = resolution + (fps,)

        return capture

    def restart(self):
        """ Try restarting this device. """
        self.stop()
        while not self.is_started:
            try:
                self.start()
            except DeviceNotConnected:
                logger.debug("Device is not connected, waiting for 1 second")
                time.sleep(1)

    @classmethod
    def _get_timestamp(cls):
        """ Get the current monotonic time from the UVC backend. """
        import uvc

        return uvc.get_time_monotonic()

    def _get_frame_and_timestamp(self, mode="img"):
        """ Get a frame and its associated timestamp. """
        import uvc

        if mode not in ("img", "bgr", "gray", "jpeg_buffer"):
            raise ValueError(f"Unsupported mode: {mode}")

        try:
            uvc_frame = self.capture.get_frame()
        except uvc.StreamError:
            logger.error("Stream error, attempting to re-init")
            self.restart()
            return self._get_frame_and_timestamp(mode=mode)

        return getattr(uvc_frame, mode), uvc_frame.timestamp

    @property
    def uvc_device_uid(self):
        """ The UID of the UVC device. """
        return self._get_uvc_device_uid(self.device_uid)

    @property
    def available_modes(self):
        """ Available frame modes for this device. """
        if self.capture is None:
            return self._get_available_modes(self.uvc_device_uid)
        else:
            return self.capture.avaible_modes  # [sic]

    @property
    def controls(self):
        """ Current controls for this device. """
        if self.capture is None:
            return self._get_controls(self.uvc_device_uid)
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


@device("video_file", optional=("topic",))
class VideoFileDevice(BaseVideoDevice):
    """ Video device that reads a video file. """

    def __init__(
        self, folder, topic, resolution=None, fps=None, loop=True,
    ):
        """ Constructor. """
        BaseVideoDevice.__init__(self, topic, resolution, fps, folder=folder)

        self.loop = loop

        self.speed = 1.0
        self._frame_index = 0
        self._last_playback_timestamp = float("nan")
        self._last_file_timestamp = float("nan")

    @classmethod
    def _from_config(cls, config, **kwargs):
        """ Per-class implementation of from_config. """
        assert device.registry[config.device_type] is cls

        cls_kwargs = cls.get_constructor_args(config)
        cls_kwargs["folder"] = kwargs.get("folder", None) or getattr(
            config, "folder", None
        )
        cls_kwargs["topic"] = config.device_uid

        return cls(**cls_kwargs)

    def start(self):
        """ Start this device. """
        if not self.is_started:
            self.capture = self._get_capture(
                self.device_uid,
                self.resolution,
                self.fps,
                **self.capture_kwargs,
            )
            if self.fps is not None:
                self.speed = self.fps / self.capture.fps

    @classmethod
    def _get_capture(cls, topic, resolution, fps, folder=None):
        """ Get a capture instance for a device by name. """
        # TODO get subsampling from resolution
        return VideoReader(folder, topic)

    def _get_frame_and_timestamp(self, mode="img"):
        """ Get a frame and its associated timestamp. """
        # TODO get gray image when mode="gray"
        if self.loop and self._frame_index >= self.capture.frame_count - 1:
            self._frame_index = 0
            self.capture.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

        _, frame = self.capture.capture.read()
        file_timestamp = (
            float(self.capture.timestamps[self._frame_index].value) / 1e9
        )
        self._frame_index += 1

        if self.speed < float("inf"):
            playback_timestamp = monotonic()
            elapsed = playback_timestamp - self._last_playback_timestamp
            desired = (file_timestamp - self._last_file_timestamp) / self.speed
            diff = desired - elapsed
            if diff > 0:
                sleep(diff)
            self._last_file_timestamp = file_timestamp
            self._last_playback_timestamp = playback_timestamp

        return frame, file_timestamp
