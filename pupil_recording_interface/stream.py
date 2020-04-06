""""""
from collections import deque
import signal
import logging
from copy import deepcopy

import numpy as np

from pupil_recording_interface.decorators import stream
from pupil_recording_interface.device import BaseDevice
from pupil_recording_interface.pipeline import Pipeline

logger = logging.getLogger(__name__)


class Packet:
    """ A data packet with a timestamp and content. """

    def __init__(
        self,
        timestamp,
        source_timestamp=None,
        source_timebase="monotonic",
        **kwargs,
    ):
        """ Constructor. """
        if source_timebase not in ("monotonic", "epoch"):
            raise ValueError(f"Unknown timebase: {source_timebase}")

        self._data = {
            "timestamp": timestamp,
            "source_timestamp": source_timestamp or timestamp,
            "source_timebase": source_timebase,
        }

        self._data.update(kwargs)

    def __getattr__(self, item):
        try:
            return self._data[item]
        except KeyError:
            raise AttributeError

    def __setattr__(self, key, value):
        if key == "_data":
            super().__setattr__(key, value)
        else:
            self._data[key] = value

    def __setitem__(self, key, value):
        self._data[key] = value

    def __getitem__(self, item):
        return self._data[item]

    def __contains__(self, item):
        return item in self._data

    def to_dict(self, deep=True):
        """ Convert to dict. """
        if deep:
            return deepcopy(self._data)
        else:
            return self._data.copy()

    def copy(self, deep=True):
        """ Create a copy of this instance. """
        return type(self)(**self.to_dict(deep=deep))


class BaseStream:
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
        self.name = name or device.device_uid

        self._last_timestamp = 0.0
        self._fps_buffer = deque(maxlen=20)

    @classmethod
    def _from_config(cls, config, device=None, folder=None):
        """ Create a stream from a StreamConfig. """
        device = device or BaseDevice.from_config(config)
        return cls(
            device,
            name=config.name,
            pipeline=Pipeline.from_config(config, device, folder),
        )

    @classmethod
    def from_config(cls, config, device=None, folder=None):
        """ Create a stream from a StreamConfig. """
        try:
            return stream.registry[config.stream_type]._from_config(
                config, device=device, folder=folder,
            )
        except KeyError:
            raise ValueError(
                f"No such stream type: {config.stream_type}. "
                f"If you are implementing a custom stream, remember to use "
                f"the @pupil_recording_interface.stream class decorator."
            )

    @property
    def current_fps(self):
        """ Current average fps. """
        if len(self._fps_buffer) == 0 or np.all(np.isnan(self._fps_buffer)):
            return float("nan")
        else:
            return np.nanmean(self._fps_buffer)

    def get_status(self):
        """ Get information about the stream status. """
        return {
            "name": self.name,
            "last_timestamp": self._last_timestamp,
            "fps": self.current_fps,
        }

    def _process_timestamp(self, timestamp):
        """ Process a new timestamp. """
        if timestamp != self._last_timestamp:
            fps = 1.0 / (timestamp - self._last_timestamp)
        else:
            fps = np.nan

        self._fps_buffer.append(fps)
        self._last_timestamp = timestamp

    def run_pre_thread_hooks(self):
        """ Run hook(s) before dispatching processing thread(s). """
        self.device.run_pre_thread_hooks()

    def start(self):
        """ Start the stream. """
        logger.debug(f"Starting stream: {self.name}")
        if not self.device.is_started:
            self.device.start()
        if self.pipeline is not None:
            self.pipeline.start()

    def get_packet(self):
        """ Get the last data packet and timestamp from the stream. """
        return self.device.get_packet()

    def stop(self):
        """ Stop the stream. """
        if self.pipeline is not None:
            self.pipeline.stop()
        if self.device.is_started:
            self.device.stop()
        logger.debug(f"Stopped stream: {self.name}")

    def run_post_thread_hooks(self):
        """ Run hook(s) after processing thread(s) finish(es). """
        self.device.run_post_thread_hooks()

    def run_in_thread(self, stop_event=None, status_queue=None):
        """ Main loop for running in a dedicated thread.

        Parameters
        ----------
        stop_event: multiprocessing.Event, optional
            An event that stops the stream in a multi-threaded setting.

        status_queue: thread safe deque, optional
            A queue for the current status in a multi-threaded setting.

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

                packet = self.get_packet()

                if self.pipeline is not None:
                    self.pipeline.flush(packet)

                # save timestamp and fps
                self._process_timestamp(packet.timestamp)

                # TODO yield stream status
                #  yield self.get_status()
                if status_queue is not None:
                    status_queue.append(self.get_status())

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


@stream("video")
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
        device = device or BaseDevice.from_config(config)
        return cls(
            device,
            name=config.name,
            pipeline=Pipeline.from_config(config, device, folder),
            color_format=config.color_format,
        )

    def get_packet(self):
        """ Get the last data packet from the stream. """
        # TODO handle uvc.StreamError and reinitialize capture
        # TODO get only jpeg buffer when not showing video
        if self.color_format == "gray":
            frame, timestamp = self.device._get_frame_and_timestamp("gray")
        else:
            frame, timestamp = self.device._get_frame_and_timestamp()

        return Packet(timestamp, frame=frame)


@stream("odometry")
class OdometryStream(BaseStream):
    """ Odometry stream. """

    def get_packet(self):
        """ Get the last data packet from the stream. """
        odometry, timestamp = self.device._get_odometry_and_timestamp()

        return Packet(timestamp, odometry=odometry)
