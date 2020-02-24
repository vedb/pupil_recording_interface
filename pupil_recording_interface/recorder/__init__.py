""""""
import abc
import os
from collections import deque

import numpy as np

from pupil_recording_interface.config import VideoConfig, OdometryConfig

class BaseRecorder(object):
    """ Base class for all recorders. """

    def __init__(self, folder, policy='new_folder'):
        """ Constructor.

        Parameters
        ----------
        folder: str
            Path to the recording folder.

        policy: str, default 'new_folder'
            Policy for recording folder creation. If 'new_folder',
            new sub-folders will be created with incremental numbering. If
            'here', the data will be recorded to the specified folder but
            will throw an error when existing files would be overwritten. If
            'overwrite', the data will be recorded to the specified folder
            and existing files will possibly be overwritten.
        """
        self.folder = self._init_folder(folder, policy)
        self.all_devices_initialized = False
        self.previous_timestamp = 0


    @classmethod
    def _init_folder(cls, folder, policy):
        """"""
        folder = os.path.abspath(os.path.expanduser(folder))

        if policy == 'new_folder':
            counter = 0
            while os.path.exists(
                    os.path.join(folder, '{:03d}'.format(counter))):
                counter += 1
            folder = os.path.join(folder, '{:03d}'.format(counter))

        elif policy == 'here':
            pass

        elif policy != 'overwrite':
            raise ValueError(
                'Unsupported file creation policy: {}'.format(policy))

        # TODO do this at the start of the recording?
        os.makedirs(folder, exist_ok=True)

        return folder


class BaseStreamRecorder(BaseRecorder):
    """ Base class for all stream recorders. """

    __metaclass__ = abc.ABCMeta

    def __init__(self, folder, device, name=None, policy='new_folder',
                 **kwargs):
        """ Constructor.

        Parameters
        ----------
        folder: str
            Path to the recording folder.

        device: BaseDevice
            The device from which to record the stream.

        name: str, optional
            The name of the recorder. If not specified, `device.uid` will be
            used.

        policy: str, default 'new_folder'
            Policy for recording folder creation. If 'new_folder',
            new sub-folders will be created with incremental numbering. If
            'here', the data will be recorded to the specified folder but
            will throw an error when existing files would be overwritten. If
            'overwrite', the data will be recorded to the specified folder
            and existing files will possibly be overwritten.
        """
        super(BaseStreamRecorder, self).__init__(folder, policy)
        self.name = name or device.uid

        self.device = device
        self.overwrite = policy == 'overwrite'

        self._timestamps = []
        self._last_timestamp = 0.
        self._fps_buffer = deque(maxlen=100)

    @classmethod
    @abc.abstractmethod
    def _from_config(cls, config, folder, device=None, overwrite=False):
        """ Per-class implementation of from_config. """

    @classmethod
    def from_config(cls, config, folder, device=None, overwrite=False):
        """ Create a recorder from a StreamConfig. """
        # TODO pass actual policy instead of overwrite
        if isinstance(config, VideoConfig):
            from .video import VideoRecorder
            return VideoRecorder._from_config(
                config, folder, device, overwrite)
        elif isinstance(config, OdometryConfig):
            from .odometry import OdometryRecorder
            return OdometryRecorder._from_config(
                config, folder, device, overwrite)
        else:
            raise TypeError('Unsupported config type: {}'.format(type(config)))

    @property
    def current_fps(self):
        """ Current average fps. """
        if len(self._fps_buffer) == 0 or np.all(np.isnan(self._fps_buffer)):
            return 0.
        else:
            return np.nanmean(self._fps_buffer)

    def _process_timestamp(self, timestamp, fps_queue=None):
        """ Process a new timestamp. """
        if timestamp != self._last_timestamp:
            fps = 1. / (timestamp - self._last_timestamp)
        else:
            fps = np.nan

        if fps_queue is not None:
            fps_queue.put(fps)
        else:
            self._fps_buffer.append(fps)

        self._last_timestamp = timestamp

    def run_pre_thread_hooks(self):
        """ Run hook(s) before dispatching the recording thread. """
        self.device.run_pre_thread_hooks()

    def start(self):
        """ Start the recorder. """
        if not self.device.is_started:
            self.device.start()

    @abc.abstractmethod
    def get_data_and_timestamp(self):
        """ Get the last data packet and timestamp from the stream. """

    @abc.abstractmethod
    def write(self, data):
        """ Write data to disk. """

    def stop(self):
        """ Stop the recorder. """
        if self.device.is_started:
            self.device.stop()

    def run_post_thread_hooks(self):
        """ Run hook(s) after the recording thread finishes. """
        self.device.run_post_thread_hooks()

    def run_in_thread(self, stop_event=None, fps_queue=None):
        """ Main recording loop for running in a dedicated thread.

        Parameters
        ----------
        stop_event: multiprocessing.Event, optional
            An event that stops recording in a multi-threaded setting.

        fps_queue: multiprocessing.Queue, optional
            A queue for the current fps in a multi-threaded setting.
        """
        self.start()
        timestamps = []

        while True:
            try:
                if stop_event is not None and stop_event.is_set():
                    break

                data, timestamp = self.get_data_and_timestamp()

                # write data to disk
                self.write(data)

                # save timestamp and fps
                # TODO ideally append directly to self._timestamps, but that
                #  blocks the thread for too long for sample rates >= 120 Hz,
                #  maybe check out how pupil does it
                self._process_timestamp(timestamp, fps_queue)
                timestamps.append(timestamp)

            except KeyboardInterrupt:
                break

        self._timestamps = timestamps
        self.stop()

    def run(self):
        """ Main recording loop. """
        self.run_pre_thread_hooks()
        self.run_in_thread()
        self.run_post_thread_hooks()