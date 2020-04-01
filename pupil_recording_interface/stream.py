""""""
import abc
import os
import shutil
import time
import json
import math
import multiprocessing as mp
from collections import deque
import signal
import uuid
import logging

import numpy as np

from pupil_recording_interface._version import __version__
from pupil_recording_interface.config import (
    VideoConfig,
    OdometryConfig,
)
from pupil_recording_interface.device.realsense import RealSenseDeviceT265
from pupil_recording_interface.device.video import (
    VideoDeviceUVC,
    VideoDeviceFLIR,
)
from pupil_recording_interface.externals.methods import get_system_info
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
        self._fps_buffer = deque(maxlen=100)

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


class StreamManager(object):
    """ Manager for multiple streams. """

    def __init__(
        self, configs, folder=None, policy="new_folder", duration=None,
    ):
        """ Constructor.

        Parameters
        ----------
        configs: iterable of StreamConfig
            An iterable of stream configurations.

        folder: str, optional
            Path to the recording folder if any of the streams are being
            recorded.

        policy: str, default 'new_folder'
            Policy for recording folder creation. If 'new_folder',
            new sub-folders will be created with incremental numbering. If
            'here', the data will be recorded to the specified folder but
            will throw an error when existing files would be overwritten. If
            'overwrite', the data will be recorded to the specified folder
            and existing files will possibly be overwritten.

        duration: float, optional
            If provided, the number of seconds after which the streams are
            stopped.
        """
        self.folder = self._init_folder(folder, policy)
        self.streams = self._init_streams(configs, self.folder)
        self.duration = duration or float("inf")
        self.stopped = False

        self._max_queue_size = 20  # max size of process fps queue
        self._start_time = 0.0
        self._start_time_monotonic = 0.0
        self._processes = {}
        self._queues = {}
        self._stop_event = None

    @classmethod
    def _init_folder(cls, folder, policy):
        """"""
        if folder is None:
            return None

        folder = os.path.abspath(os.path.expanduser(folder))

        if policy == "new_folder":
            counter = 0
            while os.path.exists(
                os.path.join(folder, "{:03d}".format(counter))
            ):
                counter += 1
            folder = os.path.join(folder, "{:03d}".format(counter))

        elif policy == "here":
            pass

        elif policy == "overwrite":
            shutil.rmtree(folder, ignore_errors=True)

        else:
            raise ValueError(
                "Unsupported file creation policy: {}".format(policy)
            )

        # TODO do this at the start of the recording?
        os.makedirs(folder, exist_ok=True)

        return folder

    @classmethod
    def _init_streams(cls, configs, folder=None):
        """ Init stream instances for all configs. """
        # mapping from uids to configs
        uids = {c.device_uid for c in configs}
        configs_by_uid = {
            uid: [c for c in configs if c.device_uid == uid] for uid in uids
        }

        devices_by_uid, streams = {}, {}
        for uid, config_list in configs_by_uid.items():
            if config_list[0].device_type == "t265":
                # init t265 device separately
                from pupil_recording_interface.device.realsense import (
                    RealSenseDeviceT265,
                )

                devices_by_uid[uid] = RealSenseDeviceT265.from_config_list(
                    config_list
                )
            else:
                devices_by_uid[uid] = None

            for config in config_list:
                # if the device for the UID has already been created, use that
                stream = BaseStream.from_config(
                    config, devices_by_uid[uid], folder
                )
                devices_by_uid[uid] = devices_by_uid[uid] or stream.device
                if config.name in streams:
                    raise ValueError(
                        "Duplicate config name: {}".format(config.name)
                    )
                streams[config.name] = stream

        return streams

    @classmethod
    def _init_processes(cls, streams, max_queue_size):
        """ Create one process for each stream instance. """
        stop_event = mp.Event()
        queues = {
            stream_name: mp.Queue(maxsize=max_queue_size)
            for stream_name in streams.keys()
        }
        processes = {
            stream_name: mp.Process(
                target=stream.run_in_thread,
                args=(stop_event, queues[stream_name]),
            )
            for stream_name, stream in streams.items()
        }

        return processes, queues, stop_event

    @classmethod
    def _start_processes(cls, processes):
        """ Start all stream processes. """
        for process_name, process in processes.items():
            logger.debug("Starting process: {}".format(process_name))
            process.start()

    @classmethod
    def _stop_processes(cls, processes, stop_event):
        """ Stop all stream processes. """
        if stop_event is not None:
            stop_event.set()
        for process_name, process in processes.items():
            logger.debug("Stopping process: {}".format(process_name))
            process.join()

    @classmethod
    def format_status(cls, status_dict):
        """ Format status dictionary to string. """
        if not any(
            math.isnan(status["fps"]) for status in status_dict.values()
        ):
            return "Sampling rates: " + ", ".join(
                "{}: {:.2f} Hz".format(name, status["fps"])
                for name, status in status_dict.items()
            )
        else:
            return None

    def save_info(self, run_duration):
        """ Save info.player.json file. """
        json_file = {
            "duration_s": run_duration,
            "meta_version": "2.1",
            "min_player_version": "1.16",
            "recording_name": self.folder,
            "recording_software_name": "pupil_recording_interface",
            "recording_software_version": __version__,
            "recording_uuid": str(uuid.uuid4()),
            "start_time_synced_s": self._start_time_monotonic,
            "start_time_system_s": self._start_time,
            "system_info": get_system_info(),
        }

        with open(
            os.path.join(self.folder, "info.player.json"),
            mode="w",
            encoding="utf-8",
        ) as f:
            json.dump(json_file, f, ensure_ascii=False, indent=4)

    def _handle_interrupt(self, signal, frame):
        """ Handle keyboard interrupt. """
        logger.debug("Caught keyboard interrupt")
        self.stopped = True

    def set_interrupt_handler(self):
        """ Set handler for keyboard interrupts. """
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def start(self):
        """ Start recording. """
        from uvc import get_time_monotonic

        # set up interrupt handler
        self.set_interrupt_handler()
        self.stopped = False

        # run hooks that need to be run in the main thread
        for stream in self.streams.values():
            stream.run_pre_thread_hooks()

        # dispatch recording threads
        self._processes, self._queues, self._stop_event = self._init_processes(
            self.streams, self._max_queue_size
        )
        self._start_processes(self._processes)

        # Record times
        self._start_time = time.time()
        self._start_time_monotonic = get_time_monotonic()

        # Log info
        if self.folder is not None:
            logger.debug("Recording folder: {}".format(self.folder))
        if self.duration < float("inf"):
            logger.debug("Streaming for {} seconds".format(self.duration))
        logger.debug("Run start time: {}".format(self._start_time))
        logger.debug(
            "Run start time monotonic: {}".format(self._start_time_monotonic)
        )

    def spin(self):
        """ Poll status queues for new data.

        Yields
        ------
        status_dict: dict
            Mapping from stream name to current status.
        """
        while (
            time.time() - self._start_time_monotonic < self.duration
            and not self.stopped
        ):
            try:
                # get fps from queues
                # TODO can the stream instance do this by itself?
                for stream_name, stream in self.streams.items():
                    while not self._queues[stream_name].empty():
                        stream._fps_buffer.append(
                            self._queues[stream_name].get()
                        )

                # yield current status for each stream
                yield {
                    c_name: c.get_status()
                    for c_name, c in self.streams.items()
                }

            except (KeyboardInterrupt, SystemExit):
                logger.debug("Stopped by keyboard interrupt.")
                break

    def stop(self):
        """ Stop streams. """
        run_duration = time.time() - self._start_time

        # stop recording threads
        self._stop_processes(self._processes, self._stop_event)

        # run hooks that need to be run in the main thread
        for stream in self.streams.values():
            stream.run_post_thread_hooks()

        # save info.player.json
        if self.folder is not None:
            self.save_info(run_duration)

        # log info
        logger.debug(
            "Stopped streams after {:.2f} seconds".format(run_duration)
        )

    def run(self):
        """ Main loop.

        Yields
        ------
        status_dict: dict
            Mapping from recorder name to current status.
        """
        self.start()
        # TODO use yield from once we drop Python 2.7
        for status_dict in self.spin():
            yield status_dict
        self.stop()
