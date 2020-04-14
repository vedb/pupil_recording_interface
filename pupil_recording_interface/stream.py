""""""
from collections import deque
import signal
import logging

import numpy as np

from pupil_recording_interface.base import BaseConfigurable
from pupil_recording_interface.decorators import stream
from pupil_recording_interface.device import BaseDevice
from pupil_recording_interface.packet import Packet
from pupil_recording_interface.pipeline import Pipeline

logger = logging.getLogger(__name__)


class BaseStream(BaseConfigurable):
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
            The name of the stream. If not specified, `device.device_uid`
            will be used.
        """
        self.device = device
        # TODO default value for pipeline?
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
            "last_timestamp": self._last_timestamp,
            "fps": self.current_fps,
        }

        if packet is not None:
            status["timestamp"] = packet.timestamp
            # TODO should this go into a dedicated "broadcasts" entry?
            for key, value in packet.get_broadcasts().items():
                status[key] = value

        return status

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

    @classmethod
    def _get_notifications(
        cls, notification_queue, priority_queue, max_len=20
    ):
        """"""
        notifications = []

        if priority_queue is not None:
            while priority_queue._getvalue():
                notifications.append(priority_queue.popleft())

        counter = 0
        if notification_queue is not None:
            while notification_queue._getvalue() and counter < max_len:
                notifications.append(notification_queue.popleft())
                counter += 1

        return notifications

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
        self.start()

        # TODO make this a little prettier to avoid the try/except block
        if stop_event is not None:
            signal.signal(signal.SIGINT, signal.SIG_IGN)

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

                if self.pipeline is not None:
                    packet = self.pipeline.flush(packet, notifications)

                # save timestamp and fps
                self._process_timestamp(packet.timestamp)

                # TODO yield self.get_status()?
                if status_queue is not None:
                    status_queue.append(self.get_status(packet))

            except KeyboardInterrupt:
                logger.debug("Thread stopped via keyboard interrupt.")
                break

        self.stop()

    def run(self):
        """ Main loop. """
        self.run_pre_thread_hooks()
        # TODO yield from self.run_in_thread()?
        self.run_in_thread()
        self.run_post_thread_hooks()


@stream("video")
class VideoStream(BaseStream):
    """ Video stream. """

    _config_attrs = {"stream_type": "video"}

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
        device: BaseDevice
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
        super(VideoStream, self).__init__(device, pipeline=pipeline, name=name)
        self.color_format = color_format

    @classmethod
    def _from_config(cls, config, device=None, folder=None):
        """ Create a stream from a StreamConfig. """
        device = device or BaseDevice.from_config(config)
        return cls(
            device,
            name=config.name or device.device_uid,
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
