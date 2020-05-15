import json
import logging
from threading import Thread
import multiprocessing as mp
import os
import shutil
import signal
import time
import uuid
from functools import reduce

from pupil_recording_interface._version import __version__
from pupil_recording_interface.decorators import device
from pupil_recording_interface.externals.methods import get_system_info
from pupil_recording_interface.stream import BaseStream
from pupil_recording_interface.utils import multiprocessing_deque, monotonic

logger = logging.getLogger(__name__)


class StreamManager(object):
    """ Manager for multiple streams. """

    def __init__(
        self,
        configs,
        folder=None,
        policy="new_folder",
        duration=None,
        update_interval=0.1,
        max_queue_size=20,
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
            and existing files will possibly be overwritten. If 'read',
            the folder is only read from, for example when using a
            'video_file' device.

        duration: float, optional
            If provided, the number of seconds after which the streams are
            stopped.

        update_interval: float, default 0.1
            Time in seconds between status and notification updates. Higher
            values might lead to to delays in communicating with the processes
            and dropped messages while lower values might lead to increased
            CPU load of the main process. Set to None for maximum update rate.
            Will be dropped in a future version with an asynchronous
            implementation of the update mechanism.

        max_queue_size: int, default 20
            Maximum size of process status and notification queues. Higher
            values might lead to delays in communicating with the processes
            while lower values might lead to dropped messages.
        """
        self.folder = self._init_folder(folder, policy)
        self.policy = policy
        self.streams = self._init_streams(configs, self.folder)
        self.duration = duration or float("inf")
        self.max_queue_size = max_queue_size
        self.update_interval = update_interval

        self.status = {}
        self.stopped = False

        self._start_time = float("nan")
        self._start_time_monotonic = float("nan")
        self._processes = {}
        self._status_queues = {}
        self._notification_queues = {}
        self._priority_queues = {}
        self._stop_event = None
        self._thread = None

    def __enter__(self):
        self.start()
        self.spin(block=False)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stopped = True
        self.stop()

    @classmethod
    def _init_folder(cls, folder, policy):
        """ Init folder if specified. """
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

        elif policy == "read":
            return folder

        else:
            raise ValueError(f"Unsupported file creation policy: {policy}")

        # TODO do this at the start of the recording?
        os.makedirs(folder, exist_ok=True)

        return folder

    @classmethod
    def _init_streams(cls, configs, folder=None):
        """ Init stream instances for all configs. """
        # mapping from uids to configs
        uids = sorted({c.device_uid for c in configs})
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
                if stream.name in streams:
                    raise ValueError(f"Duplicate stream name: {stream.name}")
                streams[stream.name] = stream

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
        priority_queues = {
            stream_name: multiprocessing_deque()
            for stream_name in streams.keys()
        }
        processes = {
            stream_name: mp.Process(
                target=stream.run_in_thread,
                args=(
                    stop_event,
                    status_queues[stream_name],
                    notification_queues[stream_name],
                    priority_queues[stream_name],
                ),
            )
            for stream_name, stream in streams.items()
        }

        return (
            processes,
            status_queues,
            notification_queues,
            priority_queues,
            stop_event,
        )

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

    def _get_status(self):
        """ Get information about the status of all streams. """
        status = {}

        for stream_name, queue in self._status_queues.items():
            if queue._getvalue():
                status[stream_name] = queue.popleft()
                if "exception" in status[stream_name]:
                    logger.error(
                        f"Stream {stream_name} has crashed with exception "
                        f"{status[stream_name]['exception']}"
                    )

        return status

    def _update_status(self, status):
        """ Update the status of all streams. """
        # TODO updating self.status should be made thread-safe
        # TODO deal with statuses that are too old or only sent once
        #  (e.g. "pattern_acquired")
        for stream_name, queue in self._status_queues.items():
            if stream_name not in self.status:
                self.status[stream_name] = self.streams[
                    stream_name
                ].get_status()  # TODO proxy for getting "empty" status
            if stream_name in status:
                self.status[stream_name].update(status[stream_name])

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
                stream_notification["name"] = source_status["name"]
                stream_notification["device_uid"] = source_status["device_uid"]
                stream_notification["timestamp"] = source_status["timestamp"]
                notifications[source_name] = stream_notification

        return notifications

    def _notify_streams(self, statuses):
        """ Notify streams of status updates they are listening for. """
        for name, stream in self.streams.items():
            notifications = self._get_notifications(statuses, stream)
            if len(notifications) > 0:
                self._notification_queues[name].append(notifications)

    def _handle_interrupt(self, signal, frame):
        """ Handle keyboard interrupt. """
        logger.debug(f"{type(self).__name__} caught keyboard interrupt")
        self.stopped = True

    def _set_interrupt_handler(self):
        """ Set handler for keyboard interrupts. """
        signal.signal(signal.SIGINT, self._handle_interrupt)

    @property
    def all_streams_running(self):
        """"""
        if self.stopped:
            return False

        for stream in self.streams:
            if stream not in self.status:
                return False
            elif "running" not in self.status[stream]:
                return False
            elif not self.status[stream]["running"]:
                return False

        return True

    @property
    def run_duration(self):
        return time.time() - self._start_time

    def send_notification(self, notification, streams=None):
        """ Send a notification over the priority queues. """
        for name, stream in self.streams.items():
            if streams is None or name in streams:
                self._priority_queues[name].append(notification)

    def await_status(self, stream, **kwargs):
        """ Wait for a stream to report a certain status. """
        # TODO timeout
        while not self.stopped:
            try:
                if all(
                    self.status[stream][key] == value
                    or key in self.status[stream]
                    and value is None
                    for key, value in kwargs.items()
                ):
                    break
            except KeyError:
                pass

    def format_status(
        self,
        key,
        format="{:.2f}",
        status_dict=None,
        max_cols=None,
        sleep=None,
    ):
        """ Format status dictionary to string. """
        status_dict = status_dict or self.status

        def recursive_get(d, *keys):
            try:
                return reduce(lambda c, k: c[k], keys, d)
            except KeyError:
                return None

        values = {
            name: recursive_get(status, *key.split("."))
            for name, status in sorted(status_dict.items())
        }

        if len(values) > 0:
            status_str = ", ".join(
                f"{name}: " + format.format(value)
                for name, value in values.items()
                if value is not None
            )
        else:
            return None

        if max_cols is not None and len(status_str) > max_cols:
            status_str = status_str[: max_cols - 3] + "..."

        if sleep:
            time.sleep(sleep)

        return status_str

    def save_info(self):
        """ Save info.player.json file. """
        json_file = {
            "duration_s": self.run_duration,
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

    def start(self):
        """ Start recording. """
        self._set_interrupt_handler()
        self.stopped = False

        # run hooks that need to be run in the main thread
        for stream in self.streams.values():
            stream.run_pre_thread_hooks()

        # dispatch recording threads
        (
            self._processes,
            self._status_queues,
            # TODO maybe rename in message_ and notification_queues?
            self._notification_queues,
            self._priority_queues,
            self._stop_event,
        ) = self._init_processes(self.streams, self.max_queue_size)
        self._start_processes(self._processes)

        # Record times
        # TODO these should be queried at the same time
        self._start_time = time.time()
        self._start_time_monotonic = monotonic()

        # Log info
        if self.folder is not None:
            logger.debug(f"Recording folder: {self.folder}")
        if self.duration < float("inf"):
            logger.debug(f"Streaming for {self.duration} seconds")
        logger.debug(f"Run start time: {self._start_time}")
        logger.debug(f"Run start time monotonic: {self._start_time_monotonic}")

    def _update(self):
        """ Update status and notify streams. """
        timestamp = time.time()
        status = self._get_status()
        self._notify_streams(status)
        self._update_status(status)
        if self.update_interval is not None:
            sleep_time = self.update_interval - (time.time() - timestamp)
            if sleep_time > 0:
                time.sleep(sleep_time)

        return status

    def _spin_blocking(self):
        """ Non-generator implementation of spin. """
        while self.run_duration < self.duration and not self.stopped:
            self._update()

        # Set stopped to True so that all_streams_running returns False
        self.stopped = True

        logger.debug("Stopped spinning")

    def spin_generator(self):
        """ Main worker loop of the manager, implemented as a generator.

        Yields
        ------
        status: dict
            A mapping from stream names to their current status.
        """
        while self.run_duration < self.duration and not self.stopped:
            status = self._update()
            yield status

    def spin(self, block=True):
        """ Main worker loop of the manager.

        Parameters
        ----------
        block: bool, default False
            If True, this method will block until the manager is stopped,
            e.g. by a keyboard interrupt. Otherwise, the main loop is
            dispatched to a separate thread which is returned by this
            function.

        Returns
        -------
        thread: threading.Thread
            If `block=True`, the Thread instance that runs the loop.
        """
        if block:
            return self._spin_blocking()
        else:
            self._thread = Thread(target=self._spin_blocking)
            self._thread.start()
            return self._thread

    def stop(self):
        """ Stop streams. """
        # save info.player.json
        if self.folder is not None and self.policy != "read":
            self.save_info()

        # stop recording threads
        self._stop_processes(self._processes, self._stop_event)

        # if we were spinning in the background, wait for thread to stop
        if self._thread is not None:
            self._thread.join()
            self._thread = None

        # run hooks that need to be run in the main thread
        for stream in self.streams.values():
            stream.run_post_thread_hooks()

        # log info
        logger.debug(f"Stopped streams after {self.run_duration:.2f} seconds")

    def run(self):
        """ Main loop (blocking). """
        self.start()
        self.spin(block=True)
        self.stop()
