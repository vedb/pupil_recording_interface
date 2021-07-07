""""""
import abc
import sys
import time
import logging
from time import monotonic, sleep

import cv2

from pupil_recording_interface.decorators import device
from pupil_recording_interface.device import BaseDevice
from pupil_recording_interface.reader.video import VideoReader
from pupil_recording_interface.errors import (
    DeviceNotConnected,
    IllegalSetting,
)
from pupil_recording_interface.externals.uvc_utils import (
    Check_Frame_Stripes,
    pre_configure_capture,
    init_exposure_handler,
)
from pupil_recording_interface.utils import SuppressStream

logger = logging.getLogger(__name__)


class BaseVideoDevice(BaseDevice):
    """ Base class for all video devices. """

    # errors that can occur during restarting
    _restart_errors = (DeviceNotConnected,)

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

        kwargs:
            Additional keyword arguments that are stored in ``capture_kwargs``
            and passed to ``get_capture()`` when starting the device.
        """
        super().__init__(device_uid)
        if not hasattr(self, "device_type"):
            # Usually set by the @device decorator, but can break things when
            # missing
            self.device_type = "video"

        self.resolution = resolution
        self.fps = fps

        self.capture = None
        self.capture_kwargs = kwargs

        self.restart_timeout = 1.0

    @property
    def is_started(self):
        return self.capture is not None

    @classmethod
    @abc.abstractmethod
    def get_capture(cls, device_uid, resolution, fps, **kwargs):
        """ Get a capture instance for a device by name. """

    @abc.abstractmethod
    def get_frame_and_timestamp(self, mode="img"):
        """ Get a frame and its associated timestamp. """

    def start(self):
        """ Start this device. """
        if not self.is_started:
            self.capture = self.get_capture(
                self.device_uid,
                self.resolution,
                self.fps,
                **self.capture_kwargs,
            )

    def stop(self):
        """ Stop this device. """
        self.capture = None

    def restart(self):
        """ Try restarting this device. """
        self.stop()
        try:
            self.start()
            logger.info(
                f"{self.device_type} device {self.device_uid} restarted"
            )
            return True
        except self._restart_errors as e:
            logger.debug(
                f"Caught error trying to reconnect {self.device_type} "
                f"device {self.device_uid}, waiting for "
                f"{self.restart_timeout} second(s): {e}"
            )
            time.sleep(self.restart_timeout)
            return False


@device("uvc")
class VideoDeviceUVC(BaseVideoDevice):
    """ UVC video device. """

    def __init__(
        self,
        device_uid,
        resolution,
        fps,
        exposure_mode="auto",
        check_stripes=False,
        controls=None,
    ):
        """ Constructor.

        Parameters
        ----------
        device_uid: str
            The name of the UVC device. For Pupil cameras, this will be
            'Pupil CamX IDY'.

        resolution: tuple, len 2
            Desired horizontal and vertical camera resolution.

        fps: int
            Desired camera refresh rate.

        exposure_mode: str, default "auto".
            Exposure mode. Can be "manual", "auto" or "forced_auto".
            Note that the "auto" mode only applies to 2nd and 3rd generation
            Pupil Core cameras. These cameras don't support auto exposure on
            the hardware so an exposure time is set by this class based on an
            average of the last camera frames. You can force this behavior with
            "forced_auto" but for 1st generation Pupil cameras it will probably
            result in under-exposed camera images. Instead, it is advised to
            set hardware auto exposure via `controls` (see below).

        controls: dict, optional
            Mapping from UVC control display names to values, e.g.
            ``{"Auto Exposure Mode": 1}``.
        """
        import uvc

        self._restart_errors = (
            DeviceNotConnected,
            uvc.InitError,
            uvc.OpenError,
        )

        super().__init__(
            device_uid, resolution, fps, user_controls=controls or {}
        )
        self.exposure_mode = exposure_mode

        # create the exposure handler for "software" auto exposure
        if (
            self.exposure_mode == "forced_auto"
            or self.exposure_mode == "auto"
            and device_uid.startswith(("Pupil Cam2", "Pupil Cam3"))
        ):
            self.exposure_handler = init_exposure_handler(fps)
            logger.debug("Software auto-exposure activated.")
        else:
            self.exposure_handler = None

        # creat the stripe detector that restarts the device when it detects
        # stripes in frames
        self.stripe_detector = Check_Frame_Stripes() if check_stripes else None

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
    def _get_uvc_capture(cls, device_uid):
        """ Get a uvc.Capture for a device for a device by UID. """
        import uvc

        try:
            return uvc.Capture(device_uid)
        except uvc.OpenError:
            # TODO could also be device already claimed
            raise DeviceNotConnected

    @classmethod
    def _get_controls(cls, capture):
        """ Get the current controls for a uvc.Capture instance. """
        return {c.display_name: c.value for c in capture.controls}

    @classmethod
    def _get_valid_controls(cls, capture):
        """ Get valid controls for a uvc.Capture instance. """
        valid_controls = {}
        for control in capture.controls:
            if control.d_type is bool:
                valid_controls[control.display_name] = (
                    control.min_val,
                    control.max_val,
                )
            if control.d_type is int:
                valid_controls[control.display_name] = range(
                    control.min_val, control.max_val, control.step
                )
            elif isinstance(control.d_type, dict):
                valid_controls[control.display_name] = control.d_type
            else:
                logger.debug(f"Unsupported control type: {control.d_type}")

        return valid_controls

    @classmethod
    def _set_controls(cls, capture, controls_dict, raise_error=True):
        """ Set controls of a uvc.Capture instance. """
        current_controls = {c.display_name: c for c in capture.controls}

        for name, value in controls_dict.items():
            if name not in current_controls:
                msg = f"Unsupported UVC control: {name}"
                if raise_error:
                    raise IllegalSetting(msg)
                else:
                    logger.error(msg)
            else:
                old_value = current_controls[name].value
                # only update if new value is different
                if value != old_value:
                    with SuppressStream(sys.stdout):
                        current_controls[name].value = value
                    if current_controls[name].value != value:
                        msg = (
                            f"Could not set UVC control {name} to {value} "
                            f"(actual value: {current_controls[name].value})"
                        )
                        if raise_error:
                            raise IllegalSetting(msg)
                        else:
                            logger.error(msg)

    @classmethod
    def get_capture(cls, uid, resolution, fps, user_controls=None):
        """ Get a capture instance for a device by name.

        Parameters
        ----------
        uid: str
            The name of the UVC device. For Pupil cameras, this will be
            'Pupil CamX IDY'.

        resolution: tuple, len 2
            Desired horizontal and vertical camera resolution.

        fps: int
            Desired camera refresh rate.

        user_controls: dict, optional
            Mapping from UVC control display names to values.
        """
        # get device uid and capture instance
        device_uid = cls._get_uvc_device_uid(uid)
        capture = cls._get_uvc_capture(device_uid)

        # set resolution and fps
        if resolution + (fps,) not in capture.avaible_modes:
            raise IllegalSetting(
                f"Unsupported frame mode: "
                f"{resolution[0]}x{resolution[1]}@{fps}fps."
            )
        capture.frame_mode = resolution + (fps,)

        # pre_configure_capture is copied from the Pupil source code a sets
        # a couple of defaults, after which the user-defined controls (if any)
        # are applied.
        capture = pre_configure_capture(capture)
        cls._set_controls(capture, user_controls, raise_error=False)

        return capture

    @classmethod
    def get_timestamp(cls):
        """ Get the current monotonic time from the UVC backend. """
        import uvc

        return uvc.get_time_monotonic()

    def get_uvc_frame(self):
        """ Grab a uvc.Frame from the device.

        Returns
        -------
        uvc.Frame:
            The captured frame.
        """
        return self.capture.get_frame()

    def get_frame_and_timestamp(self, mode="img"):
        """ Get a frame and its associated timestamp.

        Parameters
        ----------
        mode: str, default 'img'
            The type of frame to retrieve from the device. Can be 'img',
            'bgr', 'gray' or 'jpeg_buffer'.

        Returns
        -------
        frame: numpy.ndarray
            The retrieved video frame.

        timestamp: float
            The timestamp of the frame.
        """
        import uvc

        # check mode
        if mode not in ("img", "bgr", "gray", "jpeg_buffer"):
            raise ValueError(f"Unsupported mode: {mode}")

        if not self.is_started:
            # try restarting once, otherwise return a disconnect event
            if not self.restart():
                return {"name": "device_disconnect"}
        try:
            # get uvc.Frame instance and suppress stdout prints from C library
            # TODO check performance overhead of suppressing, technically it's
            #  necessary only once after starting the stream
            with SuppressStream(sys.stdout):
                uvc_frame = self.capture.get_frame(0.1)
        except (uvc.StreamError, uvc.InitError, AttributeError):
            logger.error(
                f"{self.device_type} device {self.device_uid}: "
                f"Stream error, attempting to re-init"
            )
            time.sleep(0.02)  # from pupil source code

            # try restarting once, otherwise return a disconnect event
            if self.restart():
                return self.get_frame_and_timestamp(mode=mode)
            else:
                return {"name": "device_disconnect"}

        # adjust absolute exposure time if "software" auto exposure is enabled
        if self.exposure_handler:
            target = self.exposure_handler.calculate_based_on_frame(uvc_frame)
            if target is not None:
                self._set_controls(
                    self.capture,
                    {"Absolute Exposure Time": int(target)},
                    raise_error=False,
                )

        # restart device if stripes detected in frame
        if self.stripe_detector and self.stripe_detector.require_restart(
            uvc_frame
        ):
            logger.warning(
                f"Stripes detected, restarting device {self.device_uid}"
            )
            # try restarting once, otherwise return a disconnect event
            if self.restart():
                return self.get_frame_and_timestamp(mode=mode)
            else:
                return {"name": "device_disconnect"}

        return getattr(uvc_frame, mode), uvc_frame.timestamp

    @property
    def uvc_device_uid(self):
        """ The UID of the UVC device. """
        return self._get_uvc_device_uid(self.device_uid)

    @property
    def available_modes(self):
        """ Available frame modes for this device. """
        if not self.is_started:
            capture = self._get_uvc_capture(self.uvc_device_uid)
        else:
            capture = self.capture

        return capture.avaible_modes  # [sic]

    @property
    def available_controls(self):
        """ Available UVC controls for this device. """
        if not self.is_started:
            capture = self._get_uvc_capture(self.uvc_device_uid)
        else:
            capture = self.capture

        return self._get_valid_controls(capture)

    @property
    def controls(self):
        """ Current UVC controls for this device. """
        if not self.is_started:
            capture = self._get_uvc_capture(self.uvc_device_uid)
        else:
            capture = self.capture

        return self._get_controls(capture)

    @controls.setter
    def controls(self, controls_dict):
        """ Set controls for this device. """
        if not self.is_started:
            raise RuntimeError("Device not started.")

        if not hasattr(controls_dict, "items"):
            raise ValueError("Data must be dictionary-like")

        self._set_controls(self.capture, controls_dict)


@device("video_file", optional=("topic",))
class VideoFileDevice(BaseVideoDevice):
    """ Video device that reads a video file. """

    def __init__(
        self,
        folder,
        topic,
        resolution=None,
        fps=None,
        loop=True,
        timestamps="both",
    ):
        """ Constructor. """
        BaseVideoDevice.__init__(self, topic, resolution, fps, folder=folder)

        self.loop = loop
        self.timestamps = timestamps

        self.speed = 1.0
        self._frame_index = 0
        self._last_playback_timestamp = float("nan")
        self._last_file_timestamp = float("nan")

    @classmethod
    def _from_config(cls, config, **kwargs):
        """ Per-class implementation of from_config. """
        assert device.registry[config.device_type] is cls

        cls_kwargs = cls._get_constructor_args(config)
        cls_kwargs["folder"] = kwargs.get("folder", None) or getattr(
            config, "folder", None
        )
        cls_kwargs["topic"] = config.device_uid

        return cls(**cls_kwargs)

    def start(self):
        """ Start this device. """
        if not self.is_started:
            self.capture = self.get_capture(
                self.device_uid,
                self.resolution,
                self.fps,
                **self.capture_kwargs,
            )
            self._frame_index = 0
            if self.fps is not None:
                self.speed = self.fps / self.capture.fps

    @classmethod
    def get_capture(cls, topic, resolution, fps, folder=None):
        """ Get a capture instance for a device by name. """
        # TODO get subsampling from resolution
        return VideoReader(folder, topic)

    def reset(self):
        """ Reset the video stream. """
        self.set_frame_index(0)

    def set_frame_index(self, new_index):
        """ Set frame index"""
        if not self.is_started:
            raise RuntimeError("Device is not started")

        if new_index < 0 or new_index >= self.capture.frame_count:
            raise ValueError(
                f"Index {new_index} out of range "
                f"(0-{self.capture.frame_count})"
            )

        self._frame_index = new_index
        self.capture.capture.set(cv2.CAP_PROP_POS_FRAMES, new_index)

        if new_index == 0:
            self._last_file_timestamp = float("nan")
        else:
            self._last_file_timestamp = (
                float(self.capture.timestamps[self._frame_index - 1].value)
                / 1e9
            )

    def get_frame_and_timestamp(self, mode="img"):
        """ Get a frame and its associated timestamp. """
        if not self.is_started:
            raise RuntimeError("Device is not started")

        # TODO get gray image when mode="gray"
        if self._frame_index >= self.capture.frame_count - 1:
            if self.loop:
                self.reset()
            else:
                return {"name": "stream_stop"}

        _, frame = self.capture.capture.read()
        if frame is None:
            # skip frame if it can't be read
            self.set_frame_index(self._frame_index + 1)
            return self.get_frame_and_timestamp(mode)

        file_timestamp = (
            float(self.capture.timestamps[self._frame_index].value) / 1e9
        )
        self._frame_index = self.capture.current_frame_index

        if self.speed < float("inf"):
            playback_timestamp = monotonic()
            elapsed = playback_timestamp - self._last_playback_timestamp
            desired = (file_timestamp - self._last_file_timestamp) / self.speed
            diff = desired - elapsed
            if diff > 0:
                sleep(diff)
                playback_timestamp = monotonic()
            self._last_file_timestamp = file_timestamp
            self._last_playback_timestamp = playback_timestamp
        else:
            playback_timestamp = file_timestamp

        if self.timestamps == "file":
            return frame, file_timestamp
        if self.timestamps == "playback":
            return frame, playback_timestamp
        else:
            return frame, file_timestamp, playback_timestamp
