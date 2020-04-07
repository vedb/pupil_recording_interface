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
from pupil_recording_interface.decorators import device
from pupil_recording_interface.externals.methods import get_system_info
from pupil_recording_interface.stream import BaseStream
from pupil_recording_interface.utils import multiprocessing_deque

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
        self._status_queues = {}
        self._notification_queues = {}
        self._stop_event = None
        self._status = {}

    @classmethod
    def _init_folder(cls, folder, policy):
        """"""
        if folder is None:
            return None

        folder = os.path.abspath(os.path.expanduser(folder))

        if policy == "new_folder":
            counter = 0
            while os.path.exists(os.path.join(folder, f"{counter:03d}")):
                counter += 1
            folder = os.path.join(folder, f"{counter:03d}")

        elif policy == "here":
            pass

        elif policy == "overwrite":
            shutil.rmtree(folder, ignore_errors=True)

        else:
            raise ValueError(f"Unsupported file creation policy: {policy}")

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
            # init devices with multiple configs separately
            if len(config_list) > 1:
                devices_by_uid[uid] = device.registry[
                    config_list[0].device_type
                ].from_config_list(config_list)
            else:
                devices_by_uid[uid] = None

            for config in config_list:
                # if the device for the UID has already been created, use that
                stream = BaseStream.from_config(
                    config, devices_by_uid[uid], folder
                )
                devices_by_uid[uid] = devices_by_uid[uid] or stream.device
                if config.name in streams:
                    raise ValueError(f"Duplicate config name: {config.name}")
                streams[config.name] = stream

        return streams

    @classmethod
    def _init_processes(cls, streams, max_queue_size):
        """ Create one process for each stream instance. """
        stop_event = mp.Event()
        status_queues = {
            stream_name: multiprocessing_deque(maxlen=max_queue_size)
            for stream_name in streams.keys()
        }
        notification_queues = {
            stream_name: multiprocessing_deque(maxlen=max_queue_size)
            for stream_name in streams.keys()
        }
        processes = {
            stream_name: mp.Process(
                target=stream.run_in_thread,
                args=(
                    stop_event,
                    status_queues[stream_name],
                    notification_queues[stream_name],
                ),
            )
            for stream_name, stream in streams.items()
        }

        return processes, status_queues, notification_queues, stop_event

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

    def get_status(self):
        """ Get information about the status of all streams. """
        for stream_name, queue in self._status_queues.items():
            if stream_name not in self._status:
                self._status[stream_name] = self.streams[
                    stream_name
                ].get_status()  # TODO proxy for getting "empty" status
            elif queue._getvalue():
                self._status[stream_name] = queue.popleft()

        return self._status

    @classmethod
    def _get_notifications(cls, statuses, target_stream):
        """ Get notifications for a target stream. """
        notifications = {}
        for source_name, source_status in statuses.items():
            stream_notification = {
                info: source_status[info]
                for info in target_stream.listen_for
                if info in source_status
            }
            if len(stream_notification) > 0:
                stream_notification["timestamp"] = source_status["timestamp"]
                notifications[source_name] = stream_notification

        return notifications

    def notify_streams(self, statuses):
        """ Notify streams of status updates they are listening for. """
        for name, stream in self.streams.items():
            self._notification_queues[name].append(
                self._get_notifications(statuses, stream)
            )

    @classmethod
    def format_status(cls, status_dict, value="fps", max_cols=None):
        """ Format status dictionary to string. """
        if value == "fps":
            if not any(
                math.isnan(status[value])
                for status in status_dict.values()
                if value in status
            ):
                status_str = ", ".join(
                    f"{name}: " + f"{status['fps']:.2f} Hz"
                    for name, status in status_dict.items()
                )
            else:
                return None
        elif value == "pupil_confidence":
            confidences = {
                name: status["pupil"]["confidence"]
                for name, status in status_dict.items()
                if "pupil" in status
            }
            # TODO: return None until all pupil detectors report something
            if len(confidences) > 0:
                status_str = ", ".join(
                    f"{name}: " + f"{confidence:.2f}"
                    for name, confidence in confidences.items()
                )
            else:
                return None
        else:
            raise ValueError(f"Unrecognized status value: {value}")

        if max_cols is not None and len(status_str) > max_cols:
            status_str = status_str[: max_cols - 3] + "..."

        return status_str

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
        (
            self._processes,
            self._status_queues,
            self._notification_queues,
            self._stop_event,
        ) = self._init_processes(self.streams, self._max_queue_size)
        self._start_processes(self._processes)

        # Record times
        # TODO these should be queried at the same time
        self._start_time = time.time()
        self._start_time_monotonic = get_time_monotonic()

        # Log info
        if self.folder is not None:
            logger.debug(f"Recording folder: {self.folder}")
        if self.duration < float("inf"):
            logger.debug(f"Streaming for {self.duration} seconds")
        logger.debug(f"Run start time: {self._start_time}")
        logger.debug(f"Run start time monotonic: {self._start_time_monotonic}")

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
            statuses = self.get_status()
            self.notify_streams(statuses)
            yield statuses

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
        logger.debug(f"Stopped streams after {run_duration:.2f} seconds")

    def run(self):
        """ Main loop.

        Yields
        ------
        status_dict: dict
            Mapping from legacy name to current status.
        """
        self.start()
        yield from self.spin()
        self.stop()
