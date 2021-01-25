""""""
import abc
import time
from collections import deque
import signal
import logging
from time import monotonic

import numpy as np

from pupil_recording_interface.base import BaseConfigurable
from pupil_recording_interface.decorators import stream
from pupil_recording_interface.device import BaseDevice
from pupil_recording_interface.packet import Packet
from pupil_recording_interface.pipeline import Pipeline
from pupil_recording_interface.utils import identify_process
from pupil_recording_interface.errors import DeviceNotConnected

logger = logging.getLogger(__name__)


class StreamHandler:
    """ Context manager for main loop. """

    def __init__(self, stream, status_queue=None):
        """  Constructor.

        Parameters
        ----------
        stream: BaseStream
            BaseStream instance for which to handle the main loop.

        status_queue: thread-safe deque, optional
            If specified, a last status will be sent over the queue on exit.
        """
        self.stream = stream
        self.status_queue = status_queue

    def __enter__(self):
        self.stream.start(allow_failure=True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stream.stop()
        if self.status_queue is not None:
            status = self.stream.get_status()
            if exc_type:
                status["exception"] = f"{exc_type.__name__}: {exc_val}"
            try:
                self.status_queue.append(status)
            except BrokenPipeError:
                logger.debug("Broken pipe error while sending status")

        if exc_type:
            logger.error(
                f"Stream {self.stream.name} has crashed with exception "
                f"{exc_type.__name__}: {exc_val}"
            )
            logger.debug(exc_val, exc_info=True)

        return True


class BaseStream(BaseConfigurable):
    """ Base class for all streams. """

    def __init__(self, device, pipeline=None, name=None):
        """ Constructor.

        Parameters
        ----------
        device
            The device producing the stream.

        name: str, optional
            The name of the stream. If not specified, `device.device_uid`
            will be used.
        """
        self.device = device
        self.pipeline = pipeline
        self.name = name or device.device_uid

        if self.pipeline is not None:
            self.pipeline.set_context(self)

        self._last_source_timestamp = float("nan")
        self._fps_buffer = deque(maxlen=20)

    @classmethod
    def _from_config(cls, config, device=None, folder=None):
        """ Create a stream from a StreamConfig. """
        device = device or BaseDevice.from_config(config, folder=folder)
        return cls(
            device,
            name=config.name or device.device_uid,
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
    def listen_for(self):
        if self.pipeline is not None:
            return self.pipeline.listen_for
        else:
            return []

    @property
    def current_fps(self):
        """ Current average fps. """
        if len(self._fps_buffer) == 0 or np.all(np.isnan(self._fps_buffer)):
            return float("nan")
        else:
            return np.nanmean(self._fps_buffer)

    def get_status(self, packet=None):
        """ Get information about the stream status. """
        status = {
            "name": self.name,
            "device_uid": self.device.device_uid,
            "timestamp": float("nan"),
            "source_timestamp": float("nan"),
            "last_source_timestamp": self._last_source_timestamp,
            "status_timestamp": time.time(),
            "running": False,
            "fps": self.current_fps,
        }

        if packet is not None:
            status["timestamp"] = packet.timestamp
            status["source_timestamp"] = packet.source_timestamp
            status["running"] = True
            for key, value in packet.get_broadcasts().items():
                status[key] = value

        return status

    def _process_timestamp(self, source_timestamp):
        """ Process a new timestamp. """
        if source_timestamp != self._last_source_timestamp:
            fps = 1.0 / (source_timestamp - self._last_source_timestamp)
        else:
            fps = np.nan

        self._fps_buffer.append(fps)
        self._last_source_timestamp = source_timestamp

    def run_pre_thread_hooks(self):
        """ Run hook(s) before dispatching processing thread(s). """
        self.device.run_pre_thread_hooks()

    def start(self, allow_failure=False):
        """ Start the stream. """
        logger.debug(f"Starting stream: {self.name}")

        try:
            self.device.start()
        except DeviceNotConnected:
            if allow_failure:
                logger.error(
                    f"Could not start device {self.device.device_uid} for "
                    f"stream {self.name}, will keep trying"
                )
            else:
                raise

        if self.pipeline is not None:
            self.pipeline.start()

        identify_process("stream", self.name)

    @classmethod
    def _get_notifications(
        cls, notification_queue, priority_queue, max_len=100
    ):
        """ Get notifications from notification and priority queues. """
        notifications = []

        if priority_queue is not None:
            while priority_queue._getvalue():
                notifications.append(priority_queue.popleft())

        if notification_queue is not None:
            while (
                notification_queue._getvalue() and len(notifications) < max_len
            ):
                notifications.append(notification_queue.popleft())

        return notifications

    @abc.abstractmethod
    def get_packet(self):
        """ Get a new data packet from the stream. """

    def stop(self):
        """ Stop the stream. """
        if self.pipeline is not None:
            self.pipeline.stop()
        if self.device.is_started:
            self.device.stop()
        self._fps_buffer.clear()
        logger.debug(f"Stopped stream: {self.name}")

    def run_post_thread_hooks(self):
        """ Run hook(s) after processing thread(s) finish(es). """
        self.device.run_post_thread_hooks()

    def run_in_thread(
        self,
        stop_event=None,
        status_queue=None,
        notification_queue=None,
        priority_queue=None,
    ):
        """ Main loop for running in a dedicated thread.

        Parameters
        ----------
        stop_event: multiprocessing.Event, optional
            An event that stops the stream in a multi-threaded setting.

        status_queue: thread safe deque, optional
            A queue for the current status in a multi-threaded setting.

        notification_queue: thread safe deque, optional
            A queue for incoming notifications in a multi-threaded setting.

        priority_queue: thread safe deque, optional
            A queue for incoming priority notifications in a multi-threaded
            setting.
        """
        # TODO make this a little prettier to avoid the try/except block
        if stop_event is not None:
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        with StreamHandler(self, status_queue):
            while True:
                try:
                    if stop_event is not None and stop_event.is_set():
                        logger.debug("Thread stopped via stop event.")
                        break

                    # TODO configure max number of notifications
                    notifications = self._get_notifications(
                        notification_queue, priority_queue
                    )
                    packet = self.get_packet()

                    if hasattr(packet, "event") and isinstance(
                        packet.event, dict
                    ):
                        if packet.event["name"] == "stream_stop":
                            break
                        elif packet.event["name"] == "device_disconnect":
                            # TODO send status update without manager assuming
                            #  that stream is still running
                            continue

                    if self.pipeline is not None:
                        packet = self.pipeline.process(packet, notifications)

                    self._process_timestamp(packet.source_timestamp)

                    # TODO yield self.get_status()?
                    if status_queue is not None:
                        try:
                            status_queue.append(self.get_status(packet))
                        except (ConnectionResetError, BrokenPipeError):
                            logger.debug("Error sending status to manager")

                except KeyboardInterrupt:
                    logger.debug("Thread stopped via keyboard interrupt.")
                    break

    def run(self):
        """ Main loop. """
        self.run_pre_thread_hooks()
        # TODO yield from self.run_in_thread()?
        self.run_in_thread()
        self.run_post_thread_hooks()


@stream("video")
class VideoStream(BaseStream):
    """ Video stream. """

    def __init__(
        self,
        device,
        pipeline=None,
        name=None,
        color_format="bgr24",
        side="both",
    ):
        """ Constructor.

        Parameters
        ----------
        device: BaseVideoDevice
            The device producing the stream.

        name: str, optional
            The name of the stream. If not specified, `device.device_uid`
            will be used.

        color_format: str, default 'bgr24'
            The target color format. Set to 'gray' for eye cameras.

        side: str, default 'both'
            For stereo cameras, which side to record. Can be 'left', 'right'
            or 'both'.
        """
        self.color_format = color_format
        self.side = side

        super().__init__(device, pipeline=pipeline, name=name)

    @classmethod
    def _from_config(cls, config, device=None, folder=None):
        """ Create a stream from a StreamConfig. """
        device = device or BaseDevice.from_config(config, folder=folder)
        return cls(
            device,
            name=config.name or device.device_uid,
            pipeline=Pipeline.from_config(config, device, folder),
            color_format=config.color_format,
        )

    def get_packet(self):
        """ Get the last data packet from the stream. """
        # TODO get only jpeg buffer when not showing video
        if self.color_format in ("bayer_rggb8", "gray"):
            data = self.device.get_frame_and_timestamp(self.color_format)
        else:
            data = self.device.get_frame_and_timestamp()

        if len(data) == 1:
            return Packet(
                self.name,
                self.device.device_uid,
                timestamp=monotonic(),
                event=data,
                broadcasts=["event"],
            )
        elif len(data) == 2:
            frame, timestamp = data
            source_timestamp = None
        elif len(data) == 3:
            frame, timestamp, source_timestamp = data
        else:
            raise RuntimeError(
                f"Got {len(data)} return values from get_frame_and_timestamp, "
                f"expected no more than 3"
            )

        return Packet(
            self.name,
            self.device.device_uid,
            timestamp=timestamp,
            source_timestamp=source_timestamp,
            source_timebase=self.device.timebase,
            color_format=self.color_format,
            frame=frame,
        )


@stream("motion")
class MotionStream(BaseStream):
    """ Motion data stream. """

    def __init__(self, device, motion_type, pipeline=None, name=None):
        """ Constructor.

        Parameters
        ----------
        device: BaseDevice
            The device producing the stream.

        motion_type: str
            The type of motion streamed by the device. Can be "odometry",
            "accel" or "gyro".

        name: str, optional
            The name of the stream. If not specified, `motion_type`
            will be used.
        """
        if motion_type not in ("odometry", "accel", "gyro"):
            raise ValueError(f"Unsupported motion type: {motion_type}")
        else:
            self.motion_type = motion_type

        super().__init__(
            device, pipeline=pipeline, name=name or self.motion_type
        )

    @classmethod
    def _from_config(cls, config, device=None, folder=None):
        """ Create a stream from a StreamConfig. """
        device = device or BaseDevice.from_config(config, folder=folder)
        return cls(
            device,
            config.motion_type,
            name=config.name or config.motion_type,
            pipeline=Pipeline.from_config(config, device, folder),
        )

    def get_packet(self):
        """ Get the last data packet from the stream. """
        data = self.device.get_motion_and_timestamp(self.motion_type)

        if len(data) == 1:
            return Packet(
                self.name,
                self.device.device_uid,
                timestamp=monotonic(),
                event=data,
                broadcasts=["event"],
            )
        elif len(data) == 3:
            motion, timestamp, source_timestamp = data
            return Packet(
                self.name,
                self.device.device_uid,
                timestamp=timestamp,
                source_timestamp=source_timestamp,
                source_timebase=self.device.timebase,
                **{self.motion_type: motion},
            )
        else:
            raise RuntimeError(
                f"Got {len(data)} return values from "
                f"get_motion_and_timestamp, expected 1 or 3"
            )
