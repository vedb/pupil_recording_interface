""""""
import abc
import os
from collections import deque

import numpy as np


class BaseRecorder(object):
    """ Base class for all recorders. """

    def __init__(self, folder, policy='new_folder'):
        """ Constructor.

        Parameters
        ----------
        folder : str
            Path to the recording folder.
        """
        self.folder = self._init_folder(folder, policy)

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
        """"""
        super(BaseStreamRecorder, self).__init__(folder, policy)
        self.name = name or device.uid

        self.device = device
        self.overwrite = policy == 'overwrite'

        self._timestamps = []
        self._last_timestamp = 0.
        self._fps_buffer = deque(maxlen=100)

    @classmethod
    @abc.abstractmethod
    def from_config(cls, config, folder):
        """ Create a device from a StreamConfig. """

    @abc.abstractmethod
    def start(self):
        """ Start the recorder. """

    @abc.abstractmethod
    def get_data_and_timestamp(self):
        """ Get the last data packet and timestamp from the stream. """

    @abc.abstractmethod
    def write(self, data):
        """ Write data to disk. """

    @abc.abstractmethod
    def stop(self):
        """ Stop the recorder. """

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

    def run(self, stop_event=None, fps_queue=None):
        """ Main recording loop.

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
