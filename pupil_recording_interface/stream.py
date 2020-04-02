""""""
import abc
from collections import deque
import signal
import logging

import numpy as np

from pupil_recording_interface.config import (
    VideoConfig,
    OdometryConfig,
)
from pupil_recording_interface.device.realsense import RealSenseDeviceT265
from pupil_recording_interface.device.video import (
    VideoDeviceUVC,
    VideoDeviceFLIR,
)
from pupil_recording_interface.pipeline import Pipeline

logger = logging.getLogger(__name__)


class BaseStream(object):
    """ Base class for all streams. """

    def __init__(
        self, device, pipeline=None, name=None,
    ):
        """ Constructor.

        Parameters
        ----------
        device: BaseDevice
            The device producing the stream.

        name: str, optional
            The name of the stream. If not specified, `device.uid` will be
            used.
        """
        self.device = device
        self.pipeline = pipeline
        self.name = name or device.uid

        self._last_timestamp = 0.0
        self._fps_buffer = deque(maxlen=20)

    @classmethod
    @abc.abstractmethod
    def _from_config(cls, config, device=None):
        """ Per-class implementation of from_config. """

    @classmethod
    def from_config(cls, config, device=None, folder=None):
        """ Create a stream from a StreamConfig. """
        if isinstance(config, VideoConfig):
            return VideoStream._from_config(config, device, folder)
        elif isinstance(config, OdometryConfig):
            return OdometryStream._from_config(config, device, folder)
        else:
            raise TypeError("Unsupported config type: {}".format(type(config)))

    @property
    def current_fps(self):
        """ Current average fps. """
        if len(self._fps_buffer) == 0 or np.all(np.isnan(self._fps_buffer)):
            return float("nan")
        else:
            return np.nanmean(self._fps_buffer)

    def update_status(self, queue):
        """ Update status from queue. """
        while not queue.empty():
            self._fps_buffer.append(queue.get())

    def get_status(self):
        """ Get information about the stream status. """
        return {
            "name": self.name,
            "last_timestamp": self._last_timestamp,
            "fps": self.current_fps,
        }

    def _process_timestamp(self, timestamp, fps_queue=None):
        """ Process a new timestamp. """
        if timestamp != self._last_timestamp:
            fps = 1.0 / (timestamp - self._last_timestamp)
        else:
            fps = np.nan

        if fps_queue is not None:
            fps_queue.put(fps)
        else:
            self._fps_buffer.append(fps)

        self._last_timestamp = timestamp

    def run_pre_thread_hooks(self):
        """ Run hook(s) before dispatching processing thread(s). """
        self.device.run_pre_thread_hooks()

    def start(self):
        """ Start the stream. """
        logger.debug("Starting stream: {}".format(self.name))
        if not self.device.is_started:
            self.device.start()
        if self.pipeline is not None:
            self.pipeline.start()

    def get_data_and_timestamp(self):
        """ Get the last data packet and timestamp from the stream. """
        return self.device.get_data_and_timestamp()

    def stop(self):
        """ Stop the stream. """
        if self.pipeline is not None:
            self.pipeline.stop()
        if self.device.is_started:
            self.device.stop()
        logger.debug("Stopped stream: {}".format(self.name))

    def run_post_thread_hooks(self):
        """ Run hook(s) after processing thread(s) finish(es). """
        self.device.run_post_thread_hooks()

    def run_in_thread(self, stop_event=None, fps_queue=None):
        """ Main loop for running in a dedicated thread.

        Parameters
        ----------
        stop_event: multiprocessing.Event, optional
            An event that stops the stream in a multi-threaded setting.

        fps_queue: multiprocessing.Queue, optional
            A queue for the current fps in a multi-threaded setting.

        Yields
        ------
        status: dict
            Information about the current stream status.
        """
        self.start()

        # TODO make this a little prettier to avoid the try/except block
        if stop_event is not None:
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        while True:
            try:
                if stop_event is not None and stop_event.is_set():
                    logger.debug("Thread stopped via stop event.")
                    break

                data, timestamp = self.get_data_and_timestamp()

                if self.pipeline is not None:
                    self.pipeline.flush(data, timestamp)

                # save timestamp and fps
                self._process_timestamp(timestamp, fps_queue)

                # TODO yield stream status
                #  yield self.get_status()

            except KeyboardInterrupt:
                logger.debug("Thread stopped via keyboard interrupt.")
                break

        self.stop()

    def run(self):
        """ Main loop.

        Yields
        ------
        status: dict
            Information about the current stream status.
        """
        self.run_pre_thread_hooks()
        # TODO for status in self.run_in_thread():
        #     yield status
        self.run_in_thread()
        self.run_post_thread_hooks()


class VideoStream(BaseStream):
    """ Video stream. """

    def __init__(
        self, device, pipeline=None, name=None, color_format="bgr24",
    ):
        """ Constructor.

        Parameters
        ----------
        device: BaseDevice
            The device producing the stream.

        name: str, optional
            The name of the stream. If not specified, `device.uid` will be
            used.

        color_format: str, default 'bgr24'
            The target color format. Set to 'gray' for eye cameras.
        """
        super(VideoStream, self).__init__(device, pipeline=pipeline, name=name)
        self.color_format = color_format

    @classmethod
    def _from_config(cls, config, device=None, folder=None):
        """ Create a stream from a StreamConfig. """
        if device is None:
            # TODO device = device or BaseDevice.from_config(config)
            if config.device_type == "uvc":
                device = VideoDeviceUVC(
                    config.device_uid, config.resolution, config.fps
                )
            elif config.device_type == "flir":
                device = VideoDeviceFLIR(
                    config.device_uid, config.resolution, config.fps
                )
            elif config.device_type == "t265":
                device = RealSenseDeviceT265(
                    config.device_uid,
                    config.resolution,
                    config.fps,
                    video=config.side,
                )
            else:
                raise ValueError(
                    "Unsupported device type: {}.".format(config.device_type)
                )

        return cls(
            device,
            name=config.name,
            pipeline=Pipeline.from_config(config, device, folder),
            color_format=config.color_format,
        )

    def get_data_and_timestamp(self):
        """ Get the last data packet and timestamp from the stream. """
        # TODO handle uvc.StreamError and reinitialize capture
        # TODO get only jpeg buffer when not showing video
        if self.color_format == "gray":
            frame, timestamp = self.device._get_frame_and_timestamp("gray")
        else:
            frame, timestamp = self.device._get_frame_and_timestamp()

        return frame, timestamp


class OdometryStream(BaseStream):
    """ Odometry stream. """

    @classmethod
    def _from_config(cls, config, device=None, folder=None):
        """ Per-class implementation of from_config. """
        if device is None:
            device = RealSenseDeviceT265(config.device_uid, odometry=True)

        return cls(
            device,
            name=config.name,
            pipeline=Pipeline.from_config(config, device, folder),
        )

    def get_data_and_timestamp(self):
        """ Get the last data packet and timestamp from the stream. """
        return self.device._get_odometry_and_timestamp()
