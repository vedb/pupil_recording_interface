import json
import logging
import math
import multiprocessing as mp
import os
import shutil
import signal
import time
import uuid

from pupil_recording_interface._version import __version__
from pupil_recording_interface.externals.methods import get_system_info
from pupil_recording_interface.stream import BaseStream

logger = logging.getLogger(__name__)


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
                os.path.join(folder, f"{counter:03d}")
            ):
                counter += 1
            folder = os.path.join(folder, f"{counter:03d}")

        elif policy == "here":
            pass

        elif policy == "overwrite":
            shutil.rmtree(folder, ignore_errors=True)

        else:
            raise ValueError(
                f"Unsupported file creation policy: {policy}"
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
                        f"Duplicate config name: {config.name}"
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
            logger.debug(f"Starting process: {process_name}")
            process.start()

    @classmethod
    def _stop_processes(cls, processes, stop_event):
        """ Stop all stream processes. """
        if stop_event is not None:
            stop_event.set()
        for process_name, process in processes.items():
            logger.debug(f"Stopping process: {process_name}")
            process.join()

    @classmethod
    def format_status(cls, status_dict):
        """ Format status dictionary to string. """
        if not any(
            math.isnan(status["fps"]) for status in status_dict.values()
        ):
            return ", ".join(
                f"{name}: {status['fps']:.2f} Hz"
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
            logger.debug(f"Recording folder: {self.folder}")
        if self.duration < float("inf"):
            logger.debug(f"Streaming for {self.duration} seconds")
        logger.debug(f"Run start time: {self._start_time}")
        logger.debug(
            f"Run start time monotonic: {self._start_time_monotonic}"
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
            # update status for each stream
            for stream_name, stream in self.streams.items():
                stream.update_status(self._queues[stream_name])

            # yield current status for each stream
            yield {
                c_name: c.get_status() for c_name, c in self.streams.items()
            }

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
            f"Stopped streams after {run_duration:.2f} seconds"
        )

    def run(self):
        """ Main loop.

        Yields
        ------
        status_dict: dict
            Mapping from legacy name to current status.
        """
        self.start()
        # TODO use yield from once we drop Python 2.7
        for status_dict in self.spin():
            yield status_dict
        self.stop()